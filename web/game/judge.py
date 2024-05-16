import re
import os
from fuzzywuzzy import fuzz
from qa_metrics.pedant import PEDANT

from .models import Question 

major_matcher = re.compile(r'(?<={).*?(?=})')
pedant = PEDANT()

def judge_answer_annotation_game(candidate_answer: str, question: Question):
    """Judge answer response as correct - follows QA Metrics answer verification pipeline"""
    # accept = question.answer_accept
    # reject = question.answer_reject
    # room.current_question.answer_regular_prompt,
    # room.current_question.answer_antiprompt,
    # question = room.current_question.content,
    last_clue = question.clue_list[-1]

    correct = False
    # try:
    #     prompt = f"question: {question}\nreference: {reference_answer}\ncandidate: {candidate_answer}\nIs the candidate answer correct based on the question and reference answer? Please only output 'correct' or 'incorrect'."
    #     correct = model.prompt_gpt(prompt=prompt, model_engine='gpt-4-turbo', temperature=0.1).lower() == "correct"
    # except:

    correct = []
    incorrect = []

    for ref_correct in question.answer_accept:
        correct.append(pedant.evaluate(ref_correct, candidate_answer, last_clue))
    
    for ref_reject in question.answer_reject:
        incorrect.append(pedant.evaluate(ref_reject, candidate_answer, last_clue))

    # print(question.answer_accept)
    # print(correct)
    # print(question.answer_reject)
    # print(incorrect)

    return sum(correct) > sum(incorrect)

def judge_answer_kuiperbowl(user_answer, question_answer):
    """Judge answer response as correct - follows a fuzzywuzzy string matching approach"""
    user_answer = user_answer.lower()
    question_answer = question_answer.lower()

    if user_answer == "":
        return False

    major_answers = major_matcher.findall(question_answer)
    if len(major_answers) <= 0:
        major_answers = [question_answer]
    
    r = 0.8*compare_answer_tokens(user_answer, major_answers) + \
        0.2*compare_answer_partial(user_answer, major_answers)

    return r >= 0.7


def compare_answer_tokens(user_answer, major_answers):
    """Compare by ordered tokens"""
    return max(fuzz.token_sort_ratio(user_answer, major_answer)/100 for major_answer in major_answers)

def compare_answer_partial(user_answer, major_answers):
    """Compare by partial"""
    return max(fuzz.partial_ratio(user_answer, major_answer)/100 for major_answer in major_answers)