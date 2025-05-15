"""
Abstract base class implementation of a Prompt Template. Uses a specified experiment to obtain a prompt template (e.g. f-string) that can include data inputs.
"""

from abc import ABC, abstractmethod
from model.enums import PromptType
from typing import Any

# Abstract base class for implementing prompts
class Prompt(ABC):

    def __init__(self, prompt_file, delim='\n\n'):
        self.base_prompt = ''
        if prompt_file:
            with open(prompt_file, 'r') as f:
                self.base_prompt = f.read()
            f.close()
        self.delim = delim
        
    @abstractmethod
    def create_inference_prompt(self, **kwargs):
        """Create the inference part of the prompt"""
        pass

    def create_prompt(self, **kwargs):
        """Create the full prompt"""
        return self.base_prompt + self.create_inference_prompt(**kwargs)

# LLM Persona Inference Prompts
class PairwiseComparisonUser(Prompt):
    def create_inference_prompt(self, question, plan_a, plan_b):
        return f'''You will be given a question and two step-by-step plans that could help a human user answer the question (Plan A and Plan B). Your goal is to determine which plan would help a human user answer the question more accurately and quickly. Respond with just the letter of the plan.
Question: {question}
Plan A: {plan_a}
Plan B: {plan_b}
More Helpful Plan:'''
    
class PairwiseComparison(Prompt):
    def create_inference_prompt(self, question, plan_a, plan_b):
        return f'''You will be given a question and two step-by-step plans that could help you answer the question (Plan A and Plan B). Your goal is to determine which plan would help you answer the question more accurately and quickly. Respond with just the letter of the plan.
Question: {question}
Plan A: {plan_a}
Plan B: {plan_b}
More Helpful Plan:'''
    
class ReactStarterPrompt(Prompt):
    def create_inference_prompt(self, question, plan):
        return f'''Question: {question}'''

class PromptFactory:

    def __init__(self, args: Any, prompt_type: PromptType):
        # map experiment -> prompt template
        self.prompt_type_map = {
            PromptType.pairwise_comparison: PairwiseComparison(None),
            PromptType.pairwise_comparison_user: PairwiseComparisonUser(None),
            PromptType.react: ReactStarterPrompt(f'{args.prompt_dir}/{args.inference_split}.txt')
        }
        
    def get_prompt(self, prompt_type) -> Prompt:
        if prompt_type in self.prompt_type_map:
            return self.prompt_type_map[prompt_type]
        else:
            raise ValueError(f"Unsupported Prompt type: {prompt_type}")
