from django.shortcuts import render
from .models import *
from django.db.models import Count, Avg, Case, When, Q, F, FloatField, ExpressionWrapper, Func, Value
from django.db.models.functions import Greatest, Least
from django.shortcuts import redirect
from requests_oauthlib import OAuth2Session
from django.http import JsonResponse
from django.conf import settings
import os
from dotenv import load_dotenv
load_dotenv()

# Wikimedia OAuth2 details
WIKIMEDIA_AUTHORIZE_URL = "https://en.wikipedia.org/w/rest.php/oauth2/authorize"
WIKIMEDIA_TOKEN_URL = "https://en.wikipedia.org/w/rest.php/oauth2/access_token"
WIKIMEDIA_CLIENT_ID = os.getenv('WIKIMEDIA_CLIENT_ID')
WIKIMEDIA_CLIENT_SECRET = os.getenv('WIKIMEDIA_CLIENT_SECRET')
REDIRECT_URI = "http://localhost:8000/game/oauth/callback"

def home(request):
    user_id = request.session.get('user_id')
    
    reauthenticate = request.GET.get('reauthenticate', False)

    user = None
    if user_id:
        user = User.objects.get(user_id=user_id)

    return render(request, 'game/home.html', {
        'reauthenticate': reauthenticate,
        'user': user
    })

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
    player_stats = (
        QuestionFeedback.objects
        .annotate(
            win_probability=ExpressionWrapper(
                Case(
                    When(answered_correctly=True, buzzed=True, then=Value(1.0)),
                    When(answered_correctly=False, buzzed=True, then=Value(0.0)),
                    default=Value(0),
                    output_field=FloatField()
                )
                
                * Greatest(Least(
                    0.0775 * F('buzz_position_norm') - 
                    1.278 * Square(F('buzz_position_norm')) + 
                    0.588 * Cube(F('buzz_position_norm')) + 1,
                    1), 0),
                output_field=FloatField()
            )
        )
        .values("player__user__id")
        .filter(Q(player__user__email='') & Q(player__user__email__isnull=False))
        .annotate(
            tp=Count('id', filter=Q(guessed_gen_method_correctly=True, guessed_generation_method=Question.GenerationMethod.AI)),
            fp=Count('id', filter=Q(guessed_gen_method_correctly=False, guessed_generation_method=Question.GenerationMethod.AI)),
            fn=Count('id', filter=Q(guessed_gen_method_correctly=False, guessed_generation_method=Question.GenerationMethod.HUMAN)),
            tn=Count('id', filter=Q(guessed_gen_method_correctly=True, guessed_generation_method=Question.GenerationMethod.HUMAN)),
            total=Count('id'),
            answered_correctly_count=Count('id', filter=Q(answered_correctly=True)),
            expected_wins=Avg('win_probability')
        )
        # .filter(total__gt=20)
        # .order_by('-tp')[:100] # may need to uncomment for efficiency
    )

    # Compute metrics
    leaderboard_data = []
    for player in player_stats:
        # print(player, type(player))
        tp, fp, fn, tn = player['tp'], player['fp'], player['fn'], player['tn']
        expected_wins = player['expected_wins']
        total = int(tp + fp + fn + tn)
        # accuracy = (tp + tn) / float(total) if (total) > 0 else 0
        precision = tp / float(tp + fp) if (tp + fp) > 0 else 0
        recall = tp / float(tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        # print(player)
        # print(player['player__user__id'])
        # print(User.objects.get(id=player['player__user__id']))
        leaderboard_data.append({
            'username': User.objects.get(id=player['player__user__id']).name,
            'total': total,
            'expected_wins': expected_wins,
            'f1': f1,
            # 'question_answered_correctly_rate': answered_correctly / (total) if total > 0 else 0
        })

    # Sort data by F1 score in descending order
    sorted_leaderboard = sorted(leaderboard_data, key=lambda x: x['f1'], reverse=True)
    print(sorted_leaderboard)

    return render(request, 'game/leaderboard.html', {'leaderboard_data': sorted_leaderboard})

def oauth_login(request):
    oauth_session = OAuth2Session(WIKIMEDIA_CLIENT_ID, redirect_uri=REDIRECT_URI)
    authorization_url, state = oauth_session.authorization_url(WIKIMEDIA_AUTHORIZE_URL)
    request.session['oauth_state'] = state
    print(f"Generated state: {state}")
    return redirect(authorization_url)

def oauth_callback(request):
    stored_state = request.session.get('oauth_state')
    received_state = request.GET.get('state')

    print(f"Stored state: {stored_state}")
    print(f"Received state: {received_state}")

    if stored_state != received_state:
        print("Error: State mismatch!")
        return JsonResponse({"error": "State mismatch!"}, status=400)

    oauth_session = OAuth2Session(WIKIMEDIA_CLIENT_ID, state=stored_state, redirect_uri=REDIRECT_URI)
    token = oauth_session.fetch_token(WIKIMEDIA_TOKEN_URL, authorization_response=request.build_absolute_uri(), client_secret=WIKIMEDIA_CLIENT_SECRET)

    request.session['oauth_token'] = token
    return redirect('profile')


def profile(request):
    oauth_session = OAuth2Session(WIKIMEDIA_CLIENT_ID, token=request.session.get('oauth_token'))
    response = oauth_session.get("https://en.wikipedia.org/w/api.php", params={
        'action': 'query',
        'meta': 'userinfo',
        'format': 'json'
    })
    user_info = response.json().get('query', {}).get('userinfo', {})

    # Get or create the user in the database using Wikimedia's user_id
    user, created = User.objects.get_or_create(
        user_id=user_info['id'],
        defaults={'name': user_info['name']}
    )

    request.session['user_id'] = user.user_id
    request.session['can_join_room'] = True  # Set flag to allow room joining

    # Redirect back to home after successful login
    return redirect('home')


def test_session(request):
    # Store something in the session
    request.session['test_key'] = 'test_value'

    # Retrieve it on subsequent requests
    test_value = request.session.get('test_key', 'Not Set')

    return JsonResponse({'test_key': test_value})