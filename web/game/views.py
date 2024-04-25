from django.shortcuts import render
from .models import *
from django.db.models import Count, Sum, Case, When, Q, F, FloatField

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

def leaderboard(request):
    # Get initial data grouped by player with their guessed_gen_method_correctly counts
    player_stats = (
        QuestionFeedback.objects
    .values("player__user__id")
    .annotate(
        tp=Count('id', filter=Q(guessed_gen_method_correctly=True, guessed_generation_method=Question.GenerationMethod.AI)),
        fp=Count('id', filter=Q(guessed_gen_method_correctly=False, guessed_generation_method=Question.GenerationMethod.AI)),
        fn=Count('id', filter=Q(guessed_gen_method_correctly=False, guessed_generation_method=Question.GenerationMethod.HUMAN)),
        tn=Count('id', filter=Q(guessed_gen_method_correctly=True, guessed_generation_method=Question.GenerationMethod.HUMAN)),
        total=Count('id'),
        answered_correctly_count=Count('id', filter=Q(answered_correctly=True)),
        points_scored=Sum(Case(
            When(answered_correctly=True, then=1.5 - F('buzz_position_norm')),
            default=0,
            output_field=FloatField()
        )),
        points_against=Sum(Case(
            When(answered_correctly=False, then=1.5 - F('buzz_position_norm')),
            default=0,
            output_field=FloatField()
        )),
    )
        # .filter(total__gt=20)
        # .order_by('-tp')[:100] # may need to uncomment for efficiency
    )

    # Compute metrics
    leaderboard_data = []
    for player in player_stats:
        print(player, type(player))
        tp, fp, fn, tn = player['tp'], player['fp'], player['fn'], player['tn']
        points_scored, points_against = player['points_scored'], player['points_against']
        total = int(tp + fp + fn + tn)
        # answered_correctly = player['answered_correctly']
        accuracy = (tp + tn) / float(total) if (total) > 0 else 0
        precision = tp / float(tp + fp) if (tp + fp) > 0 else 0
        recall = tp / float(tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        print(player)
        print(player['player__user__id'])
        print(User.objects.get(id=player['player__user__id']))
        leaderboard_data.append({
            'username': User.objects.get(id=player['player__user__id']).name,
            'total': total,
            'expected_wins': 1/(1 + (points_scored / ( points_against + 1e-5) ) ** 1.83),
            'f1': f1,
            # 'question_answered_correctly_rate': answered_correctly / (total) if total > 0 else 0
        })

    # Sort data by F1 score in descending order
    sorted_leaderboard = sorted(leaderboard_data, key=lambda x: x['f1'], reverse=True)
    print(sorted_leaderboard)

    return render(request, 'game/leaderboard.html', {'leaderboard_data': sorted_leaderboard})

