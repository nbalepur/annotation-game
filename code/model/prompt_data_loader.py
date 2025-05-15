"""
Abstract base class implementation of a DataFetcher. Uses a specified preference dataset and experiment to obtain a list of data inputs to use for the prompt.
"""

from model.enums import PromptType
import json
import os
import datasets
import re
from pathlib import Path
from datasets.utils.logging import disable_progress_bar
from typing import Any
disable_progress_bar()

from abc import ABC, abstractmethod

class DataFetcher(ABC):
    @abstractmethod
    def get_data(self):
        """Retrieve data from the source."""
        """Output: List of keyword arguments in dictionary form"""
        pass

    def load_hf_dataset(self, ds_name: str, split_name: str) -> Any:
        if os.path.exists(ds_name):
            ds = datasets.load_from_disk(ds_name)[split_name]
        else:
            ds = datasets.load_dataset(ds_name)[split_name]
        return ds

class DoublePlanFetcher(DataFetcher):
    """Loads the chosen and rejected plans for the model to do pairwise comparisons over"""

    def __init__(self, ds_name: str, split_name: str):
        self.ds = self.load_hf_dataset(ds_name, split_name)
    
    def parse_plan(self, plan):
        numbered_plan = [f'({idx+1}) {step}' for idx, step in enumerate(plan)]
        return ' '.join(numbered_plan)
            
    def get_data(self):
        questions, plan_a, plan_b = self.ds['question'], self.ds['plan_a'], self.ds['plan_b']
        all_prompts, all_a, all_b = questions + questions, plan_a + plan_b, plan_b + plan_a # swap orders of chosen + rejected responses
        return [{'question': p, 'plan_a': self.parse_plan(a), 'plan_b': self.parse_plan(b)} for p, a, b in list(zip(all_prompts, all_a, all_b))]
    
class DoublePlanFetcherNoSwap(DataFetcher):
    """Loads the chosen and rejected plans for the model to do pairwise comparisons over"""

    def __init__(self, ds_name: str, split_name: str):
        self.split_name = split_name
        self.ds = self.load_hf_dataset(ds_name, split_name)
    
    def parse_plan(self, plan):
        if self.split_name == 'mnemonic':
            return plan
        numbered_plan = [f'({idx+1}) {step}' for idx, step in enumerate(plan)]
        return ' '.join(numbered_plan)
            
    def get_data(self):
        questions, plan_a, plan_b = self.ds['question'], self.ds['plan_a'], self.ds['plan_b']
        return [{'question': p, 'plan_a': self.parse_plan(a), 'plan_b': self.parse_plan(b)} for p, a, b in list(zip(questions, plan_a, plan_b))]

class SinglePlanFetcher(DataFetcher):
    """Loads the singular plans for the model to run inference on"""

    def __init__(self, ds_name: str, split_name: str):
        self.ds = self.load_hf_dataset(ds_name, split_name)
            
    def get_data(self):
        questions, plan_a, plan_b = self.ds['question'], self.ds['plan_a'], self.ds['plan_b']
        all_prompts, all_plans = questions + questions, plan_a + plan_b
        return [{'question': q, 'plan': p} for q, p in list(zip(all_prompts, all_plans))]

class DataFetcherFactory:

    @staticmethod
    def get_data_fetcher(prompt_type: PromptType, args: Any):
        if prompt_type in {PromptType.pairwise_comparison, PromptType.pairwise_comparison_user}:
            return DoublePlanFetcher(ds_name=args.dataset_name, split_name=args.inference_split)
        if prompt_type in {PromptType.react}:
            return SinglePlanFetcher(ds_name=args.dataset_name, split_name=args.inference_split)
        if prompt_type in {PromptType.reward_model}:
            return DoublePlanFetcherNoSwap(ds_name=args.dataset_name, split_name=args.inference_split)
        else:
            raise ValueError(f"Unsupported DataFetcher type: {prompt_type}")