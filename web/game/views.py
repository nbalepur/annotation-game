from .models import *
from .utils import generate_id, send_email
from django.db.models import Count, Avg, Case, When, Q, F, FloatField, Func
from django.http import JsonResponse
from django.shortcuts import render, redirect
import uuid
from django.http import HttpResponse
from django.conf import settings
import os
from django.views.decorators.csrf import csrf_exempt
from scipy.stats import rankdata
import numpy as np
from dotenv import load_dotenv
from django.utils.http import urlencode
from django.urls import reverse
import json
import string
import random
load_dotenv()


def home(request):
    if 'user_id' in request.session:
        curr_user = User.objects.filter(user_id=request.session['user_id']).first()
        if curr_user is not None:
            name = curr_user.name
            return render(request, 'game/home.html', {'user_name': name, 'user_logged_in': True, 'is_password_reset': False})
    return render(request, 'game/home.html', {'user_name': '', 'user_logged_in': False, 'is_password_reset': False})


def generate_temp_password(length=8):
    """Generate a random temporary password."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def reset_password(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        email = data.get('email')
        user = User.objects.filter(email=email).first()

        if not user:
            return JsonResponse({'success': False, 'message': 'Your email address was not found. Please type the correct email, or create a new account.'}, status=404)

        # Generate a unique token
        reset_token = str(uuid.uuid4())
        user.reset_token = reset_token  # Assuming you add a reset_token field in the User model
        user.save()

        # Create the reset link
        reset_url = os.getenv('PRODUCTION_URL') + reverse('password_reset_form') + '?' + urlencode({'token': reset_token})

        # Email content
        message = f'''
        <p>Hi {user.name},</p>
        <p>You requested to reset your password. Click the link below to reset it:</p>
        <p><a href="{reset_url}">Reset My Password</a></p>
        <p>If you didn't request this, please ignore this email.</p>
        <p>Best regards,</p>
        <p>The Planorama Team</p>
        '''

        try:
            send_email(user.email, "Password Reset Request", message)
        except Exception as e:
            return JsonResponse({'success': False, 'message': 'Your email could not be sent at this time. Please try again later, or contact planstudyumd@gmail.com.'})

        return JsonResponse({'success': True, 'message': 'A password reset link has been sent to your email. Please check your spam folder!'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=400)

from django.http import JsonResponse

def password_reset_form(request):
    # Handle GET requests to render the form
    if request.method == 'GET':
        token = request.GET.get('token')  # Extract token from the query string
        if not token:
            return HttpResponse("Invalid or missing token.", status=400)

        user = User.objects.filter(reset_token=token).first()
        if not user:
            return HttpResponse("Invalid or expired token.", status=404)

        # Render the password reset form
        return render(request, 'game/home.html', {'token': token, 'is_password_reset': True, 'user_name': ''})

    # Handle POST requests to reset the password
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)  # Parse JSON payload
            token = data.get('token')
            new_password = data.get('new_password')

            if not new_password or len(new_password) < 8:
                return JsonResponse({'success': False, 'message': 'Password must be at least 8 characters.'}, status=400)

            user = User.objects.filter(reset_token=token).first()
            if not user:
                return JsonResponse({'success': False, 'message': 'Invalid or expired token.'}, status=404)

            # Update the user's password
            user.set_password(new_password)
            user.reset_token = None  # Clear the token
            user.save()

            return JsonResponse({'success': True, 'message': 'Password successfully reset.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': 'An error occurred.'}, status=500)

    # Invalid request method
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)

@csrf_exempt
def register(request):
    data = json.loads(request.body)
    email = data.get('email')
    username = data.get('username')
    password = data.get('password')


    if User.objects.filter(Q(email=email)).exists():
        return JsonResponse({'success': False, 'message': 'Email already exists. Please log in, or choose a different email.'}, status=400)
    if User.objects.filter(Q(name=username)).exists():
        return JsonResponse({'success': False, 'message': 'Username already exists. Please log in, or choose a different username.'}, status=400)

    user = User.objects.create(email=email, name=username, user_id=generate_id())
    user.set_password(password)
    user.save()

    request.session['user_id'] = user.user_id
    return JsonResponse({'success': True})

@csrf_exempt
def login(request):
    data = json.loads(request.body)
    identifier = data.get('identifier')
    password = data.get('password')

    try:
        user = User.objects.filter(Q(email=identifier) | Q(name=identifier)).get()
        if user.check_password(password):
            request.session['user_id'] = user.user_id
            return JsonResponse({'success': True})
        return JsonResponse({'success': False, 'message': 'Incorrect password for the input user'}, status=401)
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'User with the given username/email was not found'}, status=404)

def logout(request):
    request.session.flush()  # Clears session data
    return render(request, 'game/home.html', {'user_name': '', 'user_logged_in': False, 'is_password_reset': False})

def game_room(request, label):
    if 'user_id' not in request.session:
        return redirect('home')
    user = User.objects.filter(user_id=request.session['user_id']).first()
    if not user:
        return redirect('home')
    room, _ = Room.objects.get_or_create(label=label, collects_feedback=False, defaults={"max_players": 20})
    return render(request, "game/game.html", {"room": room, "user": user})

def evaluation_game_room(request, label):
    if 'user_id' not in request.session:
        return redirect('home')
    user = User.objects.filter(user_id=request.session['user_id']).first()
    if not user:
        return redirect('home')
    room, _ = Room.objects.get_or_create(label=label, collects_feedback=True, uses_instructions=True, defaults={"max_players": 1})
    return render(request, "game/game.html", {
        "room": room,
        "user": user,
        "is_pairwise": user.experiment_group == User.ExperimentGroup.PAIRWISE
    })


def instructions(request):
    if 'user_id' not in request.session:
        return redirect('home')
    user = User.objects.filter(user_id=request.session['user_id']).first()
    if not user:
        return redirect('home')
    return render(request, "base_instructions.html", {'is_pairwise': user.experiment_group == User.ExperimentGroup.PAIRWISE})

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

    # ignore tutorial + sanity check questions
    valid_logs = LeaderboardLog.objects.filter(question_id__in=Question.objects.filter(
        generation_method__in=[Question.GenerationMethod.LLAMA, 
                               Question.GenerationMethod.QWEN, 
                               Question.GenerationMethod.CLAUDE,
                               Question.GenerationMethod.GPT, 
                               Question.GenerationMethod.COMMANDR]
    ).values_list('question_id', flat=True))

    # Calculate the average correctness score and seconds taken per user based on the question type
    if question_type == Question.Category.EVERYTHING:
        aggregated_data = valid_logs.values('user_id', 'user__name').annotate(
        avg_correctness=Avg('correctness_score'),
        avg_seconds_taken=Avg(
                Case(
                    When(correctness_score__gt=0, then=F('seconds_taken')),
                    output_field=FloatField()
                )
            )
        )
        user_question_count = valid_logs.values('user').annotate(question_count=Count('question_id'))
    else:
        aggregated_data = valid_logs.filter(
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
        filtered_data = valid_logs.filter(
            question_id__in=Question.objects.filter(category=question_type).values_list('question_id', flat=True)
        )
        user_question_count = filtered_data.values('user').annotate(question_count=Count('question_id'))

    user_question_map = {row['user']: row['question_count'] for row in user_question_count}
    
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
                                 'num_questions': user_question_map[row['user_id']]})
    return leaderboard_data

def leaderboard(request):

    selected_category = request.GET.get('category', 'Overall')

    math_leaderboard = compute_leaderboard(Question.Category.MATH)
    trivia_leaderboard = compute_leaderboard(Question.Category.MULTIHOP)
    everything_leaderboard = compute_leaderboard(Question.Category.EVERYTHING)

    leaderboard_data = {
        'Math': math_leaderboard,
        'Trivia': trivia_leaderboard,
        'Overall': everything_leaderboard,
    }.get(selected_category, everything_leaderboard)

    # Render the leaderboard data to the template
    return render(request, 'game/leaderboard.html', {'leaderboard_data': leaderboard_data, 'categories': ['Overall', 'Math', 'Trivia']})
