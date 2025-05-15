"""
Enums for specific models to load and experiments to run
"""
from enum import Enum

class PromptType(Enum):
    pairwise_comparison = 'pairwise_comparison'
    pairwise_comparison_user = 'pairwise_comparison'
    react = 'react'
    reward_model = 'reward_model'

class ModelType(Enum):
    hf_chat = 'hf_chat' # huggingface
    open_ai = 'open_ai' # OpenAI
    cohere = 'cohere' # Cohere
    anthropic = 'anthropic' # Anthropic

    grm = 'grm' # generalized reward model
    qrm = 'qrm' # quantile regression
    skywork = 'skywork' # skywork reward model 
    nemotron = 'nemotron' # nvidia reward model
    internlm = 'internlm' # InternLM v2
    armorm = 'armorm' # ArmoRM (RLHFlow)
    