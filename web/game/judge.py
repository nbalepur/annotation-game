import re
import os
from fuzzywuzzy import fuzz
from qa_metrics.prompt_llm import CloseLLM
from qa_metrics.pedant import PEDANT

major_matcher = re.compile(r'(?<={).*?(?=})')
model = CloseLLM()
model.set_openai_api_key(os.getenv("OPENAI_API_KEY"))
pedant = PEDANT()

def judge_answer_annotation_game(candidate_answer, reference_answer, question, last_clue):
    """Judge answer response as correct - follows QA Metrics answer verification pipeline"""
    correct = False
    try:
        prompt = f"question: {question}\nreference: {reference_answer}\ncandidate: {candidate_answer}\nIs the candidate answer correct based on the question and reference answer? Please only output 'correct' or 'incorrect'."
        correct = model.prompt_gpt(prompt=prompt, model_engine='gpt-3.5-turbo', temperature=0.1).lower() == "correct"
    except:
        correct = pedant.evaluate(reference_answer, candidate_answer, last_clue)
    return correct

def judge_answer_kuiperbowl(user_answer, question_answer):
    """Judge answer response as correct - follows a fuzzywuzzy string matching approach"""
    user_answer = user_answer.lower()
    question_answer = question_answer.lower()

    if user_answer == "":
        return False

    major_answers = major_matcher.findall(question_answer)
    if len(major_answers) <= 0:
        major_answers = [question_answer]
    
    r = 0.8*compare_answer_tokens(user_answer, major_answers) + \
        0.2*compare_answer_partial(user_answer, major_answers)

    return r >= 0.7


def compare_answer_tokens(user_answer, major_answers):
    """Compare by ordered tokens"""
    return max(fuzz.token_sort_ratio(user_answer, major_answer)/100 for major_answer in major_answers)

def compare_answer_partial(user_answer, major_answers):
    """Compare by partial"""
    return max(fuzz.partial_ratio(user_answer, major_answer)/100 for major_answer in major_answers)