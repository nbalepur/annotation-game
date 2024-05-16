from django.shortcuts import render
from .models import *
from django.db.models import Count, Avg, Case, When, Q, F, FloatField, ExpressionWrapper, Func, Value
from django.db.models.functions import Greatest, Least

# Create your views here.
def home(request):
    return render(request, "game/home.html",{

    })

def game_room(request, label):
    room, created = Room.objects.get_or_create(label=label, collects_feedback=False, defaults={"max_players": 20})

    return render(request, "game/game.html",{
        "room":room,
    })

def evaluation_game_room(request, label):
    room, created = Room.objects.get_or_create(label=label, collects_feedback=True, defaults={"max_players": 1})

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
                    When(answered_correctly=True, then=Value(1.0)),
                    When(answered_correctly=False, then=Value(0.0)),
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
        .filter(~Q(player__user__email='') & Q(player__user__email__isnull=False))
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

