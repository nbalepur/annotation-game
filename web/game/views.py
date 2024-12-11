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
REDIRECT_URI = "http://localhost:8000/game/oauth/callback"

def home(request):
    return render(request, 'game/home.html')

def game_room(request, label):
    room, created = Room.objects.get_or_create(label=label, collects_feedback=False, defaults={"max_players": 20})

    return render(request, "game/game.html",{
        "room":room,
    })

def evaluation_game_room(request, label):
    room, created = Room.objects.get_or_create(label=label, collects_feedback=True, uses_instructions=True, defaults={"max_players": 2})
    return render(request, "game/game.html",{
        "room":room,
    })

def instructions(request):
    setting_type = os.getenv('SETTING_TYPE', 'pairwise')
    return render(request, "instructions.html", {'setting_type': setting_type})

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

def leaderboard(request):
    # First, calculate the average correctness score and seconds taken per user
    aggregated_data = LeaderboardLog.objects.values(
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

    correctness_scores = [-1 * d['avg_correctness'] for d in aggregated_data]
    correctness_rank = rankdata(correctness_scores, method='dense')

    time_scores = [d['avg_seconds_taken'] if d['avg_seconds_taken'] != None else float('inf') for d in aggregated_data]
    time_rank = rankdata(time_scores, method='dense')

    combined_rank = list(correctness_rank + time_rank)
    combined_rank_idx = np.argsort(combined_rank) # index of winners

    leaderboard_data = []
    for idx in combined_rank_idx:
        row = aggregated_data[idx]
        leaderboard_data.append({'username': row['user__name'], 
                                 'correctness': f"{'%.3f' % (row['avg_correctness'] * 100)}% Success Rate", 
                                 'time': 'N/A' if row['avg_seconds_taken'] == None else f"{'%.3f' % row['avg_seconds_taken']} Seconds", 
                                 'num_questions': len(correctness_scores)})

    # Render the leaderboard data to the template
    return render(request, 'game/leaderboard.html', {'leaderboard_data': leaderboard_data})
