
import json
import numpy as np

res_dir = '/fs/clip-quiz/nbalepur/true-helpfulness/model_code/results'
model = 'gpt-4o'
pairwise_run_name = 'run_1'
agent_run_names = ['run_1', 'run_2', 'run_3']

def load_jsonl(f_name):
    with open(f_name, 'r') as json_file:
        json_list = list(json_file)
    out = []
    for json_str in json_list:
        result = json.loads(json_str)
        out.append(result)
    return out

def parse_plan_pref(plan_text):
    if 'A' in plan_text:
        return 'A'
    if 'B' in plan_text:
        return 'B'
    return 'Tie'

aggr_pref = []
for split in ['trivia', 'math']:
    pairwise_data = load_jsonl(f'{res_dir}/{model}/{split}/{pairwise_run_name}/pairwise_comparison.jsonl')
    pairwise_labels = [parse_plan_pref(d['raw_text']) for d in pairwise_data]
    
    for idx in range(150):
        lab_normal = pairwise_labels[idx]
        lab_swap = pairwise_labels[150 + idx]
        if lab_normal == 'A' and lab_swap == 'B':
            aggr_pref.append('A')
        elif lab_normal == 'B' and lab_swap == 'A':
            aggr_pref.append('B')
        elif lab_normal == lab_swap:
            aggr_pref.append('Tie')
        else:
            print('wtf', lab_normal, lab_swap)
            exit(0)
            

from qa_metrics.pedant import PEDANT
import re
pedant = PEDANT()
import datasets

def judge_answer(candidate_answer, question, reference_answers, is_math):
    """Judge answer response as correct - follows QA Metrics answer verification pipeline"""

    if candidate_answer == "":
        return False
    
    if is_math:
        try:
            candidate_answer_clean = float(candidate_answer.strip())
            question_answer_clean = [float(a.strip()) for a in reference_answers]
            return candidate_answer_clean in question_answer_clean
        except Exception as e:
            return pedant.evaluate(reference_answers, candidate_answer, question)

    return candidate_answer in reference_answers or pedant.evaluate(reference_answers, candidate_answer, question)

ds = datasets.load_from_disk('/fs/clip-quiz/nbalepur/true-helpfulness/model_code/data/plan_inference')

aggr_agent = [{'A': {'user_id': [], 'accuracies': [], 'times': []}, 'B': {'user_id': [], 'accuracies': [], 'times': []}} for _ in range(300)]
for split in ['trivia', 'math']:
    curr_ds = ds[split]
    questions = curr_ds['question']
    answers = curr_ds['answer']
    for agent_run_name in agent_run_names:
        agent_data = load_jsonl(f'{res_dir}/{model}/{split}/{agent_run_name}/react.jsonl')
        for idx in range(150):
            d_a = agent_data[idx]
            action_a, observation_a = d_a['raw_text'][-1]['trace'][-1]['action'], d_a['raw_text'][-1]['trace'][-1]['observation']

            if 'SUBMIT_STEP' not in action_a:
                aggr_agent[idx + (150 * (split == 'math'))]['A']['accuracies'].append(-1)
            else:
                judgment = judge_answer(observation_a, questions[idx], answers[idx], split == 'math')
                if judgment == False:
                    print('A', questions[idx][:20], observation_a, answers[idx])
                aggr_agent[idx + (150 * (split == 'math'))]['A']['accuracies'].append(int(judgment))

            d_b = agent_data[150 + idx]
            action_b, observation_b = d_b['raw_text'][-1]['trace'][-1]['action'], d_b['raw_text'][-1]['trace'][-1]['observation']
            if 'SUBMIT_STEP' not in action_b:
                aggr_agent[idx + (150 * (split == 'math'))]['B']['accuracies'].append(-1)
            else:
                judgment = judge_answer(observation_b, questions[idx], answers[idx], split == 'math')
                if judgment == False:
                    print('B', questions[idx][:20], observation_b, answers[idx])
                aggr_agent[idx + (150 * (split == 'math'))]['B']['accuracies'].append(int(judgment))

            aggr_agent[idx + (150 * (split == 'math'))]['A']['times'].append(d_a['time'])
            aggr_agent[idx + (150 * (split == 'math'))]['B']['times'].append(d_b['time'])

            aggr_agent[idx + (150 * (split == 'math'))]['A']['user_id'].append(agent_run_name)
            aggr_agent[idx + (150 * (split == 'math'))]['B']['user_id'].append(agent_run_name)

for data in aggr_agent:
    for plan_id in 'AB':
        assert len(data[plan_id]['accuracies']) == 3
        assert len(data[plan_id]['times']) == 3
        assert len(data[plan_id]['user_id']) == 3

final_model_ds = {'math': {'model_comparison': [], 'A_model_accuracies': [], 'A_model_times': [], 'B_model_accuracies': [], 'B_model_times': []}, 'trivia': {'model_comparison': [], 'A_model_accuracies': [], 'A_model_times': [], 'B_model_accuracies': [], 'B_model_times': []}}

for idx, data in enumerate(aggr_agent):
    split = 'trivia' if idx < 150 else 'math'
    final_model_ds[split]['A_model_accuracies'].append(data['A']['accuracies'])
    final_model_ds[split]['B_model_accuracies'].append(data['B']['accuracies'])
    final_model_ds[split]['A_model_times'].append(data['A']['times'])
    final_model_ds[split]['B_model_times'].append(data['B']['times'])
    final_model_ds[split]['model_comparison'].append(aggr_pref[idx])

final_model_ds = datasets.DatasetDict({k: datasets.Dataset.from_dict(v) for k, v in final_model_ds.items()})
final_ds = datasets.DatasetDict({k: datasets.concatenate_datasets([ds[k], final_model_ds[k]], axis = 1) for k in ['math', 'trivia']})
print(final_ds['math'].filter(lambda ex: 'Ittymangnark' in ex['question'])['B_model_accuracies'])
#final_ds.save_to_disk('/fs/clip-quiz/nbalepur/true-helpfulness/model_code/data/plan_inference_with_models2')