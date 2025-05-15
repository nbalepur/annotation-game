"""
Abstract base class implementation of an LLM. Contains several LLM providers and ways to get LLM outputs for input prompts
"""

from abc import ABC, abstractmethod
from openai import OpenAI
from transformers import AutoTokenizer, AutoModelForSequenceClassification, AutoModel
import torch

# Abstract base class for implementing LLMs
class RewardModel(ABC):
    
    def __init__(self, args):
        self.prompt_prefix = ('Generate a keyword mnemonic to help me learn the definition for this question:' if args.inference_split == 'mnemonic' else 'Generate a plan to help me answer this question accurately and quickly:')
        pass

    @abstractmethod
    def score_plans(self, question: str, plan_a: str, plan_b: str) -> dict[str, float | str]:
        """Generate text from a prompt"""
        pass

class GRM(RewardModel):

    def __init__(self, args):
        super().__init__(args)
        # load model and tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained('Ray2333/GRM-Llama3-8B-rewardmodel-ft', cache_dir=args.cache_dir)
        self.reward_model = AutoModelForSequenceClassification.from_pretrained(
                        'Ray2333/GRM-Llama3-8B-rewardmodel-ft',
                        torch_dtype=torch.float16, 
                        cache_dir=args.cache_dir,
                        device_map='auto')
                        
        
    def score_plan(self, messages: list) -> float:
        message_template = self.tokenizer.apply_chat_template(messages, tokenize=False)
        kwargs = {"padding": 'longest', "truncation": True, "return_tensors": "pt"}
        tokens = self.tokenizer.encode_plus(message_template, **kwargs)
        with torch.no_grad():
            reward_tensor = self.reward_model(tokens["input_ids"][0].view(1,-1).to('cuda'), attention_mask=tokens["attention_mask"][0].view(1,-1).to('cuda'))[0]
            reward = reward_tensor.cpu().detach().item()
            return reward

    def score_plans(self, question: str, plan_a: str, plan_b: str):
        messages_a = [
            {'role': 'user', 'content': f"{self.prompt_prefix} {question}"},
            {'role': 'assistant', 'content': plan_a}
        ]
        messages_b = [
            {'role': 'user', 'content': f"{self.prompt_prefix} {question}"},
            {'role': 'assistant', 'content': plan_b}
        ]
        score_a, score_b = self.score_plan(messages_a), self.score_plan(messages_b)
        return {'score_a': score_a, 'score_b': score_b, 'winner': 'A' if score_a > score_b else 'B'}


class QRM(RewardModel):

    def __init__(self, args):
        super().__init__(args)
        # load model and tokenizer
        path = "nicolinho/QRM-Gemma-2-27B"
        self.model = AutoModelForSequenceClassification.from_pretrained(path, torch_dtype=torch.bfloat16, device_map='auto', trust_remote_code=True, cache_dir=args.cache_dir)
        self.tokenizer = AutoTokenizer.from_pretrained(path, use_fast=True, cache_dir=args.cache_dir)
        
    def score_plan(self, messages: list) -> float:
        input_ids = self.tokenizer.apply_chat_template(messages, return_tensors="pt").to('cuda')
        with torch.no_grad():
            output = self.model(input_ids)
            reward = output.score.cpu().float().tolist()[0][0]
            return reward

    def score_plans(self, question: str, plan_a: str, plan_b: str):
        messages_a = [
            {'role': 'user', 'content': f"{self.prompt_prefix} {question}"},
            {'role': 'assistant', 'content': plan_a}
        ]
        messages_b = [
            {'role': 'user', 'content': f"{self.prompt_prefix} {question}"},
            {'role': 'assistant', 'content': plan_b}
        ]
        score_a, score_b = self.score_plan(messages_a), self.score_plan(messages_b)
        return {'score_a': score_a, 'score_b': score_b, 'winner': 'A' if score_a > score_b else 'B'}

class InternLM(RewardModel):

    def __init__(self, args):
        super().__init__(args)
        # load model and tokenizer
        self.model = AutoModel.from_pretrained(
            "internlm/internlm2-7b-reward", 
            device_map="cuda", 
            torch_dtype=torch.float16, 
            trust_remote_code=True,
            cache_dir=args.cache_dir
        )
        self.tokenizer = AutoTokenizer.from_pretrained("internlm/internlm2-7b-reward", trust_remote_code=True, cache_dir=args.cache_dir)
        
    def score_plan(self, messages: list) -> float:
        score1 = self.model.get_score(self.tokenizer, messages)
        return score1

    def score_plans(self, question: str, plan_a: str, plan_b: str):
        messages_a = [
            {'role': 'user', 'content': f"{self.prompt_prefix} {question}"},
            {'role': 'assistant', 'content': plan_a}
        ]
        messages_b = [
            {'role': 'user', 'content': f"{self.prompt_prefix} {question}"},
            {'role': 'assistant', 'content': plan_b}
        ]
        score_a, score_b = self.score_plan(messages_a), self.score_plan(messages_b)
        return {'score_a': score_a, 'score_b': score_b, 'winner': 'A' if score_a > score_b else 'B'}

class Skywork(RewardModel):

    def __init__(self, args):
        super().__init__(args)
        # load model and tokenizer
        model_name = "Skywork/Skywork-Reward-Gemma-2-27B-v0.2"
        self.rm = AutoModelForSequenceClassification.from_pretrained(
            model_name,
            torch_dtype=torch.bfloat16,
            device_map='auto',
            cache_dir=args.cache_dir,
            num_labels=1,
        )
        self.rm_tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=args.cache_dir)
        
    def score_plan(self, messages: list) -> float:
        conv_tokenized = self.rm_tokenizer.apply_chat_template(messages, tokenize=True, return_tensors="pt").to('cuda')
        with torch.no_grad():
            score = self.rm(conv_tokenized).logits[0][0].item()
            return score

    def score_plans(self, question: str, plan_a: str, plan_b: str):
        messages_a = [
            {'role': 'user', 'content': f"{self.prompt_prefix} {question}"},
            {'role': 'assistant', 'content': plan_a}
        ]
        messages_b = [
            {'role': 'user', 'content': f"{self.prompt_prefix} {question}"},
            {'role': 'assistant', 'content': plan_b}
        ]
        score_a, score_b = self.score_plan(messages_a), self.score_plan(messages_b)
        return {'score_a': score_a, 'score_b': score_b, 'winner': 'A' if score_a > score_b else 'B'}


class Nemotron(RewardModel):

    def __init__(self, args):
        # load model and tokenizer
        super().__init__(args)
        self.client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=args.nvidia_token
        )
        
    def score_plan(self, messages: list) -> float:
        completion = self.client.chat.completions.create(
                        model="nvidia/llama-3.1-nemotron-70b-reward",
                        messages=messages)
        txt = completion.choices[0].message.content
        return float(txt[len('reward:'):])

    def score_plans(self, question: str, plan_a: str, plan_b: str):
        messages_a = [
            {'role': 'user', 'content': f"{self.prompt_prefix} {question}"},
            {'role': 'assistant', 'content': plan_a}
        ]
        messages_b = [
            {'role': 'user', 'content': f"{self.prompt_prefix} {question}"},
            {'role': 'assistant', 'content': plan_b}
        ]
        score_a, score_b = self.score_plan(messages_a), self.score_plan(messages_b)
        return {'score_a': score_a, 'score_b': score_b, 'winner': 'A' if score_a > score_b else 'B'}
    
class ArmoRMPipeline:
    def __init__(self, model_id, cache_dir, device_map="auto", torch_dtype=torch.bfloat16, truncation=True, trust_remote_code=False, max_length=4096):
        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_id,
            device_map=device_map,
            trust_remote_code=trust_remote_code,
            torch_dtype=torch_dtype,
            cache_dir=cache_dir,
        )
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_id,
            use_fast=True,
            cache_dir=cache_dir,
        )
        self.truncation = truncation
        self.device = self.model.device
        self.max_length = max_length

    def __call__(self, messages):
        """
        messages: OpenAI chat messages to be scored
        Note: no batching since due to length differences, the model will have to pad to the max length which is not efficient
        Returns: a dictionary with the score between 0 and 1
        """
        input_ids = self.tokenizer.apply_chat_template(
            messages,
            return_tensors="pt",
            padding=True,
            truncation=self.truncation,
            max_length=self.max_length,
        ).to(self.device)
        with torch.no_grad():
            output = self.model(input_ids)
            score = output.score.float().item()
        return {"score": score}

class ArmoRM(RewardModel):

    def __init__(self, args):
        super().__init__(args)
        # load model and tokenizer
        self.rm = ArmoRMPipeline("RLHFlow/ArmoRM-Llama3-8B-v0.1", cache_dir=args.cache_dir, trust_remote_code=True)
        
    def score_plan(self, messages: list) -> float:
        score1 = self.rm(messages)
        return score1['score']

    def score_plans(self, question: str, plan_a: str, plan_b: str):
        messages_a = [
            {'role': 'user', 'content': f"{self.prompt_prefix} {question}"},
            {'role': 'assistant', 'content': plan_a}
        ]
        messages_b = [
            {'role': 'user', 'content': f"{self.prompt_prefix} {question}"},
            {'role': 'assistant', 'content': plan_b}
        ]
        score_a, score_b = self.score_plan(messages_a), self.score_plan(messages_b)
        return {'score_a': score_a, 'score_b': score_b, 'winner': 'A' if score_a > score_b else 'B'}