"""
Entry point for running LLM experiments

This script:
1) Loads an LLM
2) Loads the prompts for this experiment
3) Runs (1) on (2) and saves all of the outputs
"""

# imports and directory setup
import argparse
from model.prompt_builder import PromptBuilder
from model.checkpoint_handler import Checkpoint
from model.model_loader import ModelFactory
from model.enums import ModelType, PromptType
from model.agent import Agent

import tqdm
import re

# =========================================== Argument Setup ===========================================

def setup():

    def enum_type(enum):
        enum_members = {e.name: e for e in enum}

        def converter(input):
            out = []
            for x in input.split():
                if x in enum_members:
                    out.append(enum_members[x])
                else:
                    raise argparse.ArgumentTypeError(f"You used {x}, but value must be one of {', '.join(enum_members.keys())}")
            return out

        return converter

    # hyperparameters
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run_name",
        type=str,
        help="String to identify this run",
        default="default",
    )
    parser.add_argument(
        "--model_nickname",
        type=str,
        help="Nickname of the model in directory",
        default="llama 7b",
    )
    parser.add_argument(
        "--model_name",
        type=str,
        help="Name of the model on the official API (huggingface, OpenAI, etc)",
        default="meta-llama/Llama-2-7b-hf",
    )
    parser.add_argument(
        "--model_type",
        type=enum_type(ModelType),
        help="Type of the model: hf_chat",
        default="hf_chat",
    )
    parser.add_argument(
        "--dataset_name",
        type=str,
        help="Local path or huggingface path pointing to the dataset",
        default="nbalepur/persona-inference",
    )
    parser.add_argument(
        "--inference_split",
        type=str,
        help="Split of the dataset to use",
        default="Mnemonic_val",
    )
    parser.add_argument(
        "--load_in_8bit",
        action='store_true',
        help="Should we load the model in 8 bit?",
        default=False,
    )
    parser.add_argument(
        "--load_in_4bit",
        action='store_true',
        help="Should we load the model in 4 bit?",
        default=False,
    )
    parser.add_argument(
        "--temperature",
        type=float,
        help="Temperature of the model to use",
        default=0.0,
    )
    parser.add_argument(
        "--min_tokens",
        type=int,
        help="Minimum number of tokens to generate",
        default=5,
    )
    parser.add_argument(
        "--max_tokens",
        type=int,
        help="Maximum number of tokens to generate",
        default=200,
    )
    parser.add_argument(
        "--stop_token",
        type=str,
        help="Stop token to end the generation",
        default=":)",
    )
    parser.add_argument(
        "--device_map",
        type=str,
        help="Where to load the model ('cuda', 'auto', 'cpu')",
        default="auto",
    )
    parser.add_argument(
        "--hf_token",
        type=str,
        help="Huggingface read token for access to models/datasets",
        default="",
    )
    parser.add_argument(
        "--open_ai_token",
        type=str,
        help="OpenAI token for access to the model",
        default="",
    )
    parser.add_argument(
        "--nvidia_token",
        type=str,
        help="NVIDIA token for access to the model",
        default="",
    )
    parser.add_argument(
        "--llm_proxy_token",
        type=str,
        help="LLM Proxy token for access to all models",
        default="",
    )
    parser.add_argument(
        "--cohere_token",
        type=str,
        help="Cohere token for access to the model",
        default="",
    )
    parser.add_argument(
        "--anthropic_token",
        type=str,
        help="Anthropic token for access to the model",
        default="",
    )
    parser.add_argument(
        '--prompt_types', 
        nargs='*', 
        type=enum_type(PromptType), 
        help='Prompt types/experiments to run', 
        default=[]
    )
    parser.add_argument(
        "--partition",
        type=str,
        help="Which partition should be done",
        default="none",
    )
    parser.add_argument(
        "--prompt_dir",
        type=str,
        help="Absolute directory of the prompt folder",
        default="./",
    )
    parser.add_argument(
        "--cache_dir",
        type=str,
        help="Absolute directory of the cache folder for models",
        default="./",
    )
    parser.add_argument(
        "--database_dir",
        type=str,
        help="Absolute directory of the database",
        default="./",
    )
    parser.add_argument(
        "--res_dir",
        type=str,
        help="Absolute directory of the output results folder",
        default="./",
    )
    args = parser.parse_args()
    print(args)
    return args

def main(args):

    # load model
    model_factory = ModelFactory()
    base_model = model_factory.get_model(args)

    # load checkpoints
    checkpoint_loader = Checkpoint(args)
    
    # load prompt builder
    prompt_builder = PromptBuilder(args)

    for pt in args.prompt_types[0]: # iterate through all of the experiments

        if pt == PromptType.react:
            model = Agent(args, base_model)
        else:
            model = base_model

        # set results directory for the experiment
        checkpoint_loader.set_directories(pt=pt) 

        # get prompts for the experiment
        if pt != PromptType.reward_model:
            prompts = prompt_builder.get_prompts(prompt_type=pt)
        prompt_datas = prompt_builder.get_data(prompt_type=pt)
        
        # load the current checkpoint
        start, end = checkpoint_loader.setup_partition(len(prompt_datas))
        outputs = checkpoint_loader.load_checkpoint()
        start += len(outputs)
        
        # iterate through prompts and generate outputs
        for idx in tqdm.tqdm(range(start, end)):
            prompt_data = prompt_datas[idx]
            if pt == PromptType.react:
                prompt = prompts[idx]
                out_text, time_taken = model.generate_text(prompt=prompt, prompt_data=prompt_data)
                # if 'SUBMIT_STEP' in out_text[-1]['trace'][-1]['action']:
                #     print(f"Finished with answer: {out_text[-1]['trace'][-1]['observation']}", flush=True)
                # else:
                #     print("Failed to answer", flush=True)
                outputs.append({'raw_text': out_text, 'prompt': prompt, 'time': time_taken})
            elif pt == PromptType.reward_model:
               out_data = model.score_plans(question=prompt_data['question'], plan_a=prompt_data['plan_a'], plan_b=prompt_data['plan_b'])
               outputs.append({'raw_text': out_data, 'prompt': prompt_data})
            else:
                prompt = prompts[idx]
                out_text = model.generate_text(prompt=prompt)
                outputs.append({'raw_text': out_text, 'prompt': prompt})
                # print(out_text, flush=True)
            checkpoint_loader.save_checkpoint(outputs=outputs, is_final=False)

        # final save
        checkpoint_loader.save_checkpoint(outputs=outputs, is_final=True)

if __name__ == '__main__':
    args = setup()
    main(args)
