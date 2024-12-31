from django.shortcuts import render
from .models import *
from django.db.models import Count, Avg, Case, When, Q, F, FloatField, ExpressionWrapper, Func, Value, OuterRef
from django.db.models.functions import Greatest, Least, Rank
from django.db.models.expressions import Window
from django.shortcuts import redirect
from requests_oauthlib import OAuth2Session
from django.http import JsonResponse
from django.conf import settings
import os
from scipy.stats import rankdata
import numpy as np
from dotenv import load_dotenv
load_dotenv()

# Wikimedia OAuth2 details
WIKIMEDIA_AUTHORIZE_URL = "https://en.wikipedia.org/w/rest.php/oauth2/authorize"
WIKIMEDIA_TOKEN_URL = "https://en.wikipedia.org/w/rest.php/oauth2/access_token"
WIKIMEDIA_CLIENT_ID = os.getenv('WIKIMEDIA_CLIENT_ID')
WIKIMEDIA_CLIENT_SECRET = os.getenv('WIKIMEDIA_CLIENT_SECRET')

def home(request):
    return render(request, 'game/home.html')

def game_room(request, label):
    room, created = Room.objects.get_or_create(label=label, collects_feedback=False, defaults={"max_players": 20})

    return render(request, "game/game.html",{
        "room":room,
    })

def evaluation_game_room(request, label):
    room, created = Room.objects.get_or_create(label=label, collects_feedback=True, uses_instructions=True, defaults={"max_players": 1})
    return render(request, "game/game.html",{
        "room":room,
    })

def instructions(request):
    return render(request, "base_instructions.html", {})

def instructions_default(request):
    return render(request, "instructions/default.html", {})

def instructions_modal_pairwise(request):
    return render(request, "instructions/pairwise_phase_panel.html", {})

def instructions_modal_swap(request):
    return render(request, "instructions/swap_phase_panel.html", {})

def incentives(request):
    return render(request, "incentives.html", {})

def resources(request):
    return render(request, "resources.html", {})

class Square(Func):
    function = 'POW'
    template = '%(function)s(%(expressions)s, 2)'

class Cube(Func):
    function = 'POW'
    template = '%(function)s(%(expressions)s, 3)'

def compute_leaderboard(question_type: Question.Category):

    # Calculate the average correctness score and seconds taken per user based on the question type
    if question_type == Question.Category.EVERYTHING:
        aggregated_data = LeaderboardLog.objects.values('user_id', 'user__name').annotate(
        avg_correctness=Avg('correctness_score'),
        avg_seconds_taken=Avg(
                Case(
                    When(correctness_score__gt=0, then=F('seconds_taken')),
                    output_field=FloatField()
                )
            )
        )
    else:
        aggregated_data = LeaderboardLog.objects.filter(
            question_id__in=Question.objects.filter(category=question_type).values('question_id')
        ).values(
            'user_id', 'user__name'
        ).annotate(
            avg_correctness=Avg('correctness_score'),
            avg_seconds_taken=Avg(
                Case(
                    When(correctness_score__gt=0, then=F('seconds_taken')),
                    output_field=FloatField()
                )
            )
        )
    aggregated_data = list(aggregated_data)

    # Rank the users by corectnesss and time
    correctness_scores = [-1 * d['avg_correctness'] for d in aggregated_data]
    correctness_rank = rankdata(correctness_scores, method='dense')

    time_scores = [d['avg_seconds_taken'] if d['avg_seconds_taken'] != None else float('inf') for d in aggregated_data]
    time_rank = rankdata(time_scores, method='dense')

    # Aggregate ranks
    combined_rank = list(correctness_rank + time_rank)
    combined_rank_idx = np.argsort(combined_rank)

    # Build leaderbaord data
    leaderboard_data = []
    for idx in combined_rank_idx:
        row = aggregated_data[idx]
        leaderboard_data.append({'username': row['user__name'], 
                                 'correctness': f"{'%.3f' % (row['avg_correctness'] * 100)}% Accuracy", 
                                 'time': 'N/A' if row['avg_seconds_taken'] == None else f"{'%.3f' % row['avg_seconds_taken']} Seconds", 
                                 'num_questions': len(correctness_scores)})
    return leaderboard_data

def leaderboard(request):

    selected_category = request.GET.get('category', 'Overall')

    math_leaderboard = compute_leaderboard(Question.Category.MATH)
    trivia_leaderboard = compute_leaderboard(Question.Category.MULTIHOP)
    everything_leaderboard = compute_leaderboard(Question.Category.EVERYTHING)

    print('leaderboard:', everything_leaderboard)

    leaderboard_data = {
        'Math': math_leaderboard,
        'Trivia': trivia_leaderboard,
        'Overall': everything_leaderboard,
    }.get(selected_category, everything_leaderboard)

    # Render the leaderboard data to the template
    return render(request, 'game/leaderboard.html', {'leaderboard_data': leaderboard_data, 'categories': ['Overall', 'Math', 'Trivia']})
