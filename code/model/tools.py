from sympy import sqrt, Abs, pi
from sympy.core.sympify import SympifyError
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
)
from text_unidecode import unidecode
import os
import requests
import re
import random
import nltk
from bs4 import BeautifulSoup
from model.document_cache import DocumentCache
from dotenv import load_dotenv
import cohere


load_dotenv('planorama.env')

class ToolBox:

    def __init__(self, args):
        self.document_cache = DocumentCache(f'{args.database_dir}/document_cache.db')
        self.curr_page = None
        self.curr_title = None
        self.CONTEXT_WINDOW = 5

    def retrieve_from_document_cache(self, key: str):
        return self.document_cache.retrieve_from_document_cache(key)

    def add_to_document_cache(self, key: str, value: str):
        self.document_cache.add_to_document_cache(key, value)

    def parse_tool_call(self, tool_str: str):
        match = re.match(r"(\w+)\((.*)\)$", tool_str.strip())
        if match:
            tool_name = match.group(1)
            inputs = match.group(2)  # Keep everything inside the parentheses as input
            return {"tool_name": tool_name, "tool_input": inputs}
        return None

    def call_tool(self, tool_str: str):
        parsed_tool = self.parse_tool_call(tool_str)
        if parsed_tool == None:
            return {"result": "ERROR. The tool input was improperly formatted", "finished": False}
        tool_name, tool_input = parsed_tool['tool_name'], parsed_tool['tool_input']

        if tool_name == "SUBMIT_STEP":
            return {"result": tool_input, "finished": True}
        if tool_name == "CALCULATE":
            return self.calculator(tool_input) | {"finished": False}
        if tool_name == "SEARCH":
            return self.web_search_and_retrieve(tool_input) | {"finished": False}
            # return self.web_search(tool_input) | {"finished": False}
        if tool_name == "FIND_ON_PAGE":
            return self.select_content(tool_input) | {"finished": False}
        
        return {"result": "ERROR. That is not a valid action", "finished": False}


    def extract_elements_from_html(self, html: str):
        soup = BeautifulSoup(html, "lxml")
        elements = soup.find_all(id=re.compile(r"^element-"))
        sentences = []
        for elem in elements:
            sentences.append(elem.text.strip())
        return sentences

    def clean_query(self, query):
        """Clean the query for cached lookup"""
        return unidecode(query)

    def calculator(self, equation):
        """Executes the calculator tool using SymPy with implicit multiplication handling"""

        # Define allowed symbols and functions
        allowed_symbols = {
            "sqrt": sqrt,
            "abs": Abs,
            "round": round,
            "pi": pi,  # Include 'pi' if you want to allow it
        }

        # Set up the transformations to include implicit multiplication
        transformations = standard_transformations + (
            implicit_multiplication_application,
        )

        try:
            # Parse the expression using parse_expr with allowed symbols and transformations
            expr = parse_expr(
                equation,
                local_dict=allowed_symbols,
                transformations=transformations,
                evaluate=True,
            )

            # Evaluate the expression numerically
            result = expr.evalf()
            # Apply rounding to 4 decimal places
            result = round(float(result), 4)
            return {'result': result}
        except Exception as _:
            return {"result": "ERROR. The equation was invalid"}
        
    def get_wiki_pages(self, query):
        """Get the Wikipedia page based on the query"""

        query = self.clean_query(query)
        cached_query_res = self.retrieve_from_document_cache(
            "wiki_title_query:" + query
        )
        if cached_query_res is not None:
            return cached_query_res, "from_cache"

        try:
            api_key = os.getenv("GOOGLE_API_KEY")
            search_engine_id = os.getenv("GOOGLE_CSE_ID")
            google_search_url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": api_key,
                "cx": search_engine_id,
                "q": query,
                "num": 10,
            }

            response = requests.get(google_search_url, params=params)
            response.raise_for_status()
            response_data = response.json()
            search_results = response_data.get("items", [])
            if not search_results:
                return ["Your search returned no Wikipedia pages"], "error"
                    
        except Exception as e:
            return [str(e)], "error"
        
        search_res = [r["title"].replace(" - Wikipedia", "").strip() for _, r in enumerate(search_results)]
        search_res = '<split>'.join(search_res)
        self.add_to_document_cache(
            "wiki_title_query:" + query, search_res
        )
        return search_res, "new_search"

    def get_html_sentences(self, p_tag_input):
        # Build a merged list of items, where each item is either a plain string
        # or a tuple (html_fragment, text_content) for certain tags.
        merged_items = []  # We'll merge adjacent text nodes on the fly.

        def append_item(item):
            """Append item merging with previous if both are plain text."""
            if isinstance(item, str):
                if merged_items and isinstance(merged_items[-1], str):
                    merged_items[-1] += item
                else:
                    merged_items.append(item)
            else:
                merged_items.append(item)

        # Process each child in one loop.
        for c in p_tag_input.children:
            if c.name == 'sup':
                continue  # Skip superscript elements.
            elif c.name in ('i', 'b'):
                # Keep the tag element: store tuple (HTML, text).
                append_item((str(c), c.text))
            elif c.name == 'a' and c.get('href') and c.get('href').startswith('/wiki/') and ':' not in c.get('href'):
                append_item((str(c), c.text))
            elif c.name not in {'style'}:
                # For other cases, we’re only interested in text.
                append_item(c.text)

        # Normalize all items to be tuples: (html_fragment, text_content)
        merged_items = [
            (s, s) if isinstance(s, str) else (s[0], s[1])
            for s in merged_items
        ]

        # Build the full text (by joining the text content) for sentence tokenization.
        full_text = ''.join(text for (_, text) in merged_items)
        sentences = [s + ' ' for s in nltk.sent_tokenize(full_text)]

        return sentences

    def web_search_and_retrieve(self, query):

        web_out = self.web_search(query)
        if "error" in web_out['result'].lower():
            return web_out
        match = re.search(r'<Title>(.*?)</Title><Content>(.*?)</Content>', web_out['result'], re.DOTALL)
        if not match:
            print('error:', web_out, flush=True)
            return {'result': "ERROR. Parsing failed"}
        title = match.group(1)
        web_content = match.group(2)

        search_out = self.select_content(query)
        if "error" in search_out['result'].lower():
            return search_out
        match = re.search(r'<Title>(.*?)</Title><Content>(.*?)</Content>', search_out['result'], re.DOTALL)
        if not match:
            print('error:', search_out, flush=True)
            return {'result': "ERROR. Parsing failed"}
        search_content = match.group(2)
        
        format_result = f'<Title>{title}</Title><First Paragraph>{web_content}</First Paragraph><Selected Content>{search_content}</Selected Content>'
        return {"result": format_result}

    def web_search(self, query, use_headers=True):
        """Perform a web search"""

        wiki_pages, status = self.get_wiki_pages(query)
        # print(wiki_pages, status)
        if status == "error":
            return {'result': "ERROR. The Wikipedia page does not exist"}
            
        #print("found pages", datetime.datetime.now().time())
        
        for page_title in wiki_pages.split("<split>"):
            # print("Trying page:", page_title)
            page_title_clean = page_title

            cached_page_res = self.retrieve_from_document_cache(
                "wiki_page_query:" + page_title_clean
            )
            if cached_page_res is not None:
                # print('cached page!')
                title, first_paragraph, all_sentences = cached_page_res.split("<delim>")
                self.curr_page = all_sentences
                self.curr_title = title
                return {'result': f"<Title>{title}</Title><Content>{first_paragraph}</Content>"}

            params = {
                "action": "parse",
                "page": page_title,
                "format": "json",
                "prop": "text",
                "redirects": 1,
            }

            try:
                api_url = "https://en.wikipedia.org/w/api.php"
                rand_idx = random.choice(list(range(0, 3)))
                WIKI_TOKENS = [os.getenv(f'WIKIMEDIA_API_KEY{token_num}') for token_num in range(1, 4)]
                USER_AGENTS = [os.getenv(f'USER_AGENT{token_num}')  for token_num in range(1, 4)]
                wiki_token, user_agent = WIKI_TOKENS[rand_idx], USER_AGENTS[rand_idx]
                headers = {
                    "Authorization": f"Bearer {wiki_token}",
                    "User-Agent": user_agent,
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }

                response = requests.get(api_url, params=params, headers=headers if use_headers else {})
                if response.status_code == 403 or response.headers.get(
                    "mediawiki-api-error", ""
                ) == "mwoauth-invalid-authorization-invalid-user":
                    print("WIKIMEDIA KEY THROWING ERROR")

                if response.status_code == 200:
                    data = response.json()

                    if "error" in data:
                        if use_headers and "invalid" in data["error"]["info"] or "forbidden" in data["error"]["info"]:
                            print("WIKIMEDIA KEY THROWING ERROR, TRYING WITH DEFAULT KEY")
                            return self.web_search(query, False)
                        return {'result': 'ERROR. The web search failed.'}
                    
                    html_content = data["parse"]["text"]["*"]
                    title = data["parse"]["title"]
                    soup = BeautifulSoup(html_content, "lxml")

                    
                    # content = f'Title: {title} | Content: {first_paragraph_text}'
                    # self.add_to_document_cache(
                    #     "wiki_page_query:" + page_title_clean, content
                    # )
                    # return {'result': content}


                    all_sentences = []
                    first_paragraph = []
                    for p_tag in soup.find_all('p'):
                        html_sentences = self.get_html_sentences(p_tag)
                        add_to_first = first_paragraph == []
                        for sent in html_sentences:
                            if sent:
                                all_sentences.append(sent)
                                if add_to_first:
                                    first_paragraph.append(sent)

                    all_sentences = '<split>'.join(all_sentences)
                    first_paragraph = ' '.join(first_paragraph)
                    content = f'{title}<delim>{first_paragraph}<delim>{all_sentences}'
                    self.add_to_document_cache(
                        "wiki_page_query:" + page_title_clean, content
                    )
                    self.curr_page = all_sentences
                    self.curr_title = title
                    return {'result': f"<Title>{title}</Title><Content>{first_paragraph}</Content>"}

            except Exception as e:
                print(e)
                return {'result': 'ERROR'}
                continue

        return {'result': 'ERROR. The web search failed'}
    
    def select_content(self, query: str):
        """Executes the content selection tool"""
        if self.curr_page == None or self.curr_title == None:
            return {"result": "ERROR. You must call SEARCH before LOOKUP"}
        
        docs = self.curr_page.split('<split>')
        if len(docs) <= self.CONTEXT_WINDOW:
            doc_content = ' '.join(docs)
            content = f'<Title>{self.curr_title}</Title><Content>{doc_content}</Content>'
            return {"result": content}

        cohere_client = cohere.ClientV2(api_key=os.getenv("COHERE_API_KEY"))

        try:
            retr_results = cohere_client.rerank(
                model="rerank-english-v3.0",
                query=query,
                documents=docs,
                top_n=1,
                return_documents=True,
            )
            retr_index = retr_results.results[0].index
            if isinstance(retr_index, list):
                retr_index = retr_index[0]
            lower_bound = retr_index - (self.CONTEXT_WINDOW // 2)
            upper_bound = retr_index + (self.CONTEXT_WINDOW // 2)
            if lower_bound < 0:
                upper_bound += abs(lower_bound)
                lower_bound = 0
            if upper_bound > len(docs) - 1:
                lower_bound -= abs(upper_bound - (len(docs) - 1))
                upper_bound = len(docs) - 1
            doc_subset = docs[lower_bound:upper_bound+1]
            doc_content = ' '.join(doc_subset)
            content = f'<Title>{self.curr_title}</Title><Content>{doc_content}</Content>'
            return {"result": content}
        except Exception as e:
            print(e)
            return {"result": "ERROR. The conent selection failed"}