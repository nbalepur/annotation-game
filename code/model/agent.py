from model.tools import ToolBox
import time
import copy


class Agent:

    def __init__(self, args, llm):
        self.MAX_RUNS_PER_STEP = 5
        self.memory = []

        self.args = args
        self.llm = llm
        self.toolbox = ToolBox(self.args)
        pass

    """
    Question: {question}
    
    Step 1: {step1}
    Thought 1: [generate]
    Action 1: [generate]
    Observation 1: [paste from tool output]
    
    ...

    Answer to Step 1: {answer}
    [repeat]
    """
    def generate_text(self, prompt, prompt_data):
        start_time = time.time()

        self.memory = []
        base_prompt = copy.deepcopy(prompt)

        step_idx = 0
        steps = prompt_data['plan']

        while step_idx < len(steps):

            step_memory = {
                'step': steps[step_idx],
                'trace': [],
            }
        
            base_prompt += f'\n---\nStep {step_idx+1}: {steps[step_idx]}'

            for _ in range(self.MAX_RUNS_PER_STEP):

                # thought generation
                base_prompt += f'\nThought:'
                self.llm.stop_token = ['Action:', 'Step:', 'Observation:']
                generated_thought = self.llm.generate_text(base_prompt).strip()
                if 'Thought:' in generated_thought:
                    generated_thought = generated_thought.replace('Thought:', '').strip()

                # print(generated_thought)

                # action generation
                base_prompt += ' ' + generated_thought
                base_prompt += f'\nAction:'
                self.llm.stop_token = ['Thought:', 'Step:', 'Observation:']
                generated_action = self.llm.generate_text(base_prompt).strip()
                if 'Action:' in generated_action:
                    generated_action = generated_action.replace('Action:', '').strip()

                # print(generated_action)

                # observation
                base_prompt += ' ' + generated_action
                tool_output = self.toolbox.call_tool(generated_action)
                observation, finished = tool_output['result'], tool_output['finished']
                
                
                # are we done?
                if finished:
                    base_prompt += f"\nAnswer to Step {step_idx+1}: {observation}"
                else: 
                    base_prompt += f"\nObservation: {observation}"
                    base_prompt += '\n'

                step_memory['trace'].append({
                    'thought': generated_thought,
                    'action': generated_action,
                    'observation': observation
                })

                if finished:
                    break

            self.memory.append(step_memory)
            step_idx += 1

        return self.memory, time.time() - start_time
