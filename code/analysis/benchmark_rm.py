import datasets
import json
import numpy as np
from sklearn.metrics import accuracy_score

plan_ds = datasets.load_dataset('nbalepur/planorama_irt_swap', cache_dir='/fs/clip-scratch/nbalepur/cache')
mnemonic_ds = datasets.load_from_disk('/fs/clip-quiz/nbalepur/true-helpfulness/model_code/data/mnemonic_inference_with_learn')

ds = {'math': plan_ds['math'], 'trivia': plan_ds['trivia'], 'mnemonic': mnemonic_ds['mnemonic']}

def load_json(f):
    with open(f, 'r') as json_file:
        json_list = list(json_file)
    out = []
    for json_str in json_list:
        result = json.loads(json_str)
        out.append(result)
    return out

def majority_vote(votes):
    if votes.count("A") == votes.count("B"):
        return "Tie"
    return "B" if votes.count("A") < votes.count("B") else "A"

def acc_score(win1, win2):
    scores = []
    for w1, w2 in zip(win1, win2):
        if w2 == 'Tie':
            continue
        if w1 == 'Tie':
            scores.append(0.5)
        else:
            scores.append(float(w1 == w2))
    return f"{100.0 * np.mean(scores):.3f}"

models = ['grm', 'nemotron', 'qrm', 'skywork', 'internlm', 'armorm']
for split in ['math', 'trivia']:

    human_a_help, human_b_help = ds[split]['A_human_helpfulness'], ds[split]['B_human_helpfulness']
    model_a_help, model_b_help = ds[split]['A_model_helpfulness'], ds[split]['B_model_helpfulness']
    human_labels, model_labels = [], []
    for idx in range(5):
        human_labels.append([0 if a > b else 1 for a, b in zip(human_a_help, human_b_help)])
        model_labels.append([0 if a > b else 1 for a, b in zip(model_a_help, model_b_help)])
    human_downstream = ['A' if not x else 'B' for x in (np.mean(human_labels, axis=0) > 0.5)]
    model_downstream = ['A' if not x else 'B' for x in (np.mean(model_labels, axis=0) > 0.5)]

    human_pairwise = [majority_vote(votes) for votes in ds[split]['human_comparisons']]
    model_pairwise = ds[split]['model_comparison']

    print("Split:", split)
    print('\n\n')
    for m in models:
        f = f'/fs/clip-quiz/nbalepur/true-helpfulness/model_code/results/{m}/{split}/run_1/reward_model.jsonl'
        out = load_json(f)
        winners = [x['raw_text']['winner'] for x in out]

        print("Model:", m)
        print("Humans Pick:", acc_score(winners, human_pairwise))
        print("Helps Humans:", acc_score(winners, human_downstream))
        
        print("Models Pick:", acc_score(winners, model_pairwise))
        print("Helps Models:", acc_score(winners, model_downstream))
        

        print('\n\n')

# import numpy as np
# for split in ['mnemonic']:
    
#     human_pairwise = ds[split]['pairwise_comparison']
#     learn_a, learn_b = ds[split]['learn_a'], ds[split]['learn_b']
#     human_a_help, human_b_help = learn_a, learn_b
#     valid_idxs = [idx for idx in range(len(learn_a)) if human_pairwise[idx] != 'Tie' and learn_a[idx] != [] and learn_b[idx] != [] and np.mean(learn_a[idx]) != np.mean(learn_b[idx])]
#     human_downstream = ['A' if np.mean(human_a_help[idx]) > np.mean(human_b_help[idx]) else 'B' for idx in range(len(learn_a))]

#     print("Split:", split)
#     print('\n\n')
#     for m in models:
#         f = f'/fs/clip-quiz/nbalepur/true-helpfulness/model_code/results/{m}/{split}/run_1/reward_model.jsonl'
#         out = load_json(f)
#         winners = [x['raw_text']['winner'] for x in out]

#         valid_idxs = [idx for idx in range(len(winners)) if human_pairwise[idx] != 'Tie' and human_pairwise[idx] != 'Tie']

#         print("Model:", m)
#         print("Helps Humans:", acc_score(winners, human_downstream))
#         print("Humans Pick:", acc_score(winners, human_pairwise))

#         print('\n\n')

