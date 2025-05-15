"""
Abstract base class implementation of an LLM. Contains several LLM providers and ways to get LLM outputs for input prompts
"""

from abc import ABC, abstractmethod
from model.enums import ModelType
from model.reward_model_loader import *
import time
import openai
import anthropic
import cohere
import torch
from transformers import AutoTokenizer, pipeline
from huggingface_hub import HfFolder

# Abstract base class for implementing LLMs
class LLM(ABC):

    def __init__(self):
        pass

    @abstractmethod
    def generate_text(self, prompt: str) -> str:
        """Generate text from a prompt"""
        pass

class HuggingFaceChatModel(LLM):

    def __init__(self, hf_model_name: str, temp: float, min_length: int, max_length: int, load_in_4bit: bool, load_in_8bit: bool, device_map: str, cache_dir: str, hf_token: str):

        self.temp = temp
        self.min_length = min_length
        self.max_length = max_length

        HfFolder.save_token(hf_token)

        # load tokenizer
        tokenizer = AutoTokenizer.from_pretrained(hf_model_name, cache_dir=cache_dir)
        dtype = {
            "bf16": torch.bfloat16,
            "fp32": torch.float32,
            "fp16": torch.float16,
            "auto": "auto",
        }['auto']
        pipe = pipeline(
            'text-generation',
            model=hf_model_name,
            tokenizer=tokenizer,
            device_map=device_map,
            torch_dtype=dtype,
            min_new_tokens=min_length,
            max_new_tokens=max_length,
            model_kwargs={"cache_dir": cache_dir, "do_sample": False, "load_in_4bit": load_in_4bit, "load_in_8bit": load_in_8bit}
        )
        self.pipe = pipe
        self.tokenizer = tokenizer

    def generate_text(self, prompt: str) -> str | None:

        messages = [{"role": "user", "content": prompt}]

        if self.temp == 0.0:
            return self.pipe(messages, 
            do_sample=False,  
            min_new_tokens=self.min_length, 
            max_new_tokens=self.max_length,
            return_full_text=False)[0]['generated_text'].strip()
        else:
            return self.pipe(messages, 
            do_sample=True, 
            temperature=self.temp, 
            min_new_tokens=self.min_length, 
            max_new_tokens=self.max_length,
            return_full_text=False)[0]['generated_text'].strip()

class OpenAI(LLM):

    def __init__(self, openai_model_name: str, temp: float, max_length: int, stop_token: str, openai_token: str):

        self.temp = temp
        self.openai_model_name = openai_model_name
        self.max_length = max_length
        self.stop_token = stop_token
        self.openai_token = openai_token

    def generate_text_helper(self, prompt: str, num_sec=0, max_retries=5) -> str | None:

        if num_sec == max_retries:
            print("MAX RETRIES EXCEDED")
            return None

        time.sleep(2**(num_sec - 1))

        try:
            client = openai.OpenAI(api_key=self.openai_token)
            response = client.chat.completions.create(
                        model=self.openai_model_name,
                        messages=[
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=self.max_length,
                        stop=self.stop_token,
                        temperature=self.temp)
            return response.choices[0].message.content

        except Exception as e:
            print(e)
            return self.generate_text_helper(prompt, num_sec=num_sec+1, max_retries=max_retries)

    def generate_text(self, prompt) -> str | None:
        
        return self.generate_text_helper(prompt, num_sec=0, max_retries=3)

class Cohere(LLM):

    def __init__(self, cohere_model_name: str, temp: float, max_length: int, stop_token: str, cohere_token: str):

        self.temp = temp
        self.cohere_model_name = cohere_model_name
        self.max_length = max_length
        self.stop_token = stop_token
        self.co = cohere.Client(cohere_token)

    def generate_text_helper(self, prompt, num_sec=0, max_retries=5):

        if num_sec == max_retries:
            print("MAX RETRIES EXCEDED")
            return None

        time.sleep(2**(num_sec))

        try:
            response = self.co.chat(
                message=prompt,
                max_tokens=self.max_length,
                model=self.cohere_model_name,
                stop_sequences=[self.stop_token],
                temperature=self.temp,
            )
            return response.text

        except Exception as e:
            return self.generate_text_helper(prompt, num_sec=num_sec+1, max_retries=max_retries)

    def generate_text(self, prompt):
        return self.generate_text_helper(prompt, num_sec=0, max_retries=3)

class Anthropic(LLM):

    def __init__(self, model_name, temp, max_length, stop_token, anthropic_token):

        self.temp = temp
        self.model_name = model_name
        self.max_length = max_length
        self.stop_token = stop_token
        self.client = anthropic.Anthropic(api_key=anthropic_token)

    def generate_text_helper(self, prompt, num_sec=0, max_retries=5):

        if num_sec == max_retries:
            print("MAX RETRIES EXCEDED")
            return None

        time.sleep(2**(num_sec))

        try:
            message = self.client.messages.create(
                model=self.model_name,
                max_tokens=self.max_length,
                temperature=self.temp,
                stop_sequences=[self.stop_token],
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )
            return message.content[0].text

        except Exception as e:
            return self.generate_text_helper(prompt, num_sec=num_sec+1, max_retries=max_retries)

    def generate_text(self, prompt):
        return self.generate_text_helper(prompt, num_sec=0, max_retries=3)

class ModelFactory:

    @staticmethod
    def get_model(args):
        if args.model_type[0] == ModelType.hf_chat:
            return HuggingFaceChatModel(hf_model_name=args.model_name, temp=args.temperature, min_length=args.min_tokens, max_length=args.max_tokens, load_in_4bit=args.load_in_4bit, load_in_8bit=args.load_in_8bit, device_map=args.device_map, cache_dir=args.cache_dir, hf_token=args.hf_token)
        
        if args.model_type[0] == ModelType.open_ai:
            return OpenAI(openai_model_name=args.model_name, temp=args.temperature, max_length=args.max_tokens, stop_token=args.stop_token, openai_token=args.open_ai_token)

        if args.model_type[0] == ModelType.cohere:
            return Cohere(cohere_model_name=args.model_name, temp=args.temperature, max_length=args.max_tokens, stop_token=args.stop_token, cohere_token=args.cohere_token)

        if args.model_type[0] == ModelType.anthropic:
            return Anthropic(model_name=args.model_name, temp=args.temperature, max_length=args.max_tokens, stop_token=args.stop_token, anthropic_token=args.anthropic_token)

        if args.model_type[0] == ModelType.grm:
            return GRM(args)

        if args.model_type[0] == ModelType.qrm:
            return QRM(args)

        if args.model_type[0] == ModelType.skywork:
            return Skywork(args)

        if args.model_type[0] == ModelType.nemotron:
            return Nemotron(args)
        
        if args.model_type[0] == ModelType.internlm:
            return InternLM(args)

        if args.model_type[0] == ModelType.armorm:
            return ArmoRM(args)

        else:
            raise ValueError(f"Unsupported Model type: {args.model_type[0]}")
