"""
Helper functions/class to retrieve prompts for a specific experiment. Prompts consist of two parts:
1) a prompt template (e.g. f-string)
2) a list of data inputs (keyword arguments) that can infill the prompt template
Combining (1) and (2), you get a list of prompts
"""

from model.prompt_template_loader import PromptFactory, PromptType
from model.prompt_data_loader import DataFetcherFactory

class PromptBuilder:

    def __init__(self, args):
        self.args = args

    def get_prompts(self, prompt_type: PromptType):

        # data inputs used to infill the prompt template
        data_factory = DataFetcherFactory()
        data_fetcher = data_factory.get_data_fetcher(prompt_type=prompt_type, args=self.args)
        prompt_inputs = data_fetcher.get_data()

        # template for the prompt
        prompt_factory = PromptFactory(args=self.args, prompt_type=prompt_type)
        prompt_parser = prompt_factory.get_prompt(prompt_type)

        prompts = [None if p == None else prompt_parser.create_prompt(**p) for p in prompt_inputs]
        return prompts
    
    def get_data(self, prompt_type: PromptType):
        data_factory = DataFetcherFactory()
        data_fetcher = data_factory.get_data_fetcher(prompt_type=prompt_type, args=self.args)
        prompt_inputs = data_fetcher.get_data()
        return prompt_inputs