from django.shortcuts import render
from .models import *
from django.db.models import Count, Q, F

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
        .values("player__user__name")
        .annotate(
            tp=Count('id', filter=Q(guessed_gen_method_correctly=True, guessed_generation_method=Question.GenerationMethod.AI)),
            fp=Count('id', filter=Q(guessed_gen_method_correctly=False, guessed_generation_method=Question.GenerationMethod.AI)),
            fn=Count('id', filter=Q(guessed_gen_method_correctly=False, guessed_generation_method=Question.GenerationMethod.HUMAN)),
            tn=Count('id', filter=Q(guessed_gen_method_correctly=True, guessed_generation_method=Question.GenerationMethod.HUMAN)),
            total=Count('id'),
            answered_correctly=Count('id', filter=Q(answered_correctly=True)),
        )
        # .filter(total__gt=5)
        # .order_by('-tp')[:100] # may need to uncomment for efficiency
    )

    # Compute metrics
    leaderboard_data = []
    for player in player_stats:
        print(player, type(player))
        tp, fp, fn, tn = player['tp'], player['fp'], player['fn'], player['tn']
        total = int(tp + fp + fn + tn)
        answered_correctly = player['answered_correctly']
        accuracy = (tp + tn) / float(total) if (total) > 0 else 0
        precision = tp / float(tp + fp) if (tp + fp) > 0 else 0
        recall = tp / float(tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        leaderboard_data.append({
            'username': player['player__user__name'],
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'total': total,
            'f1': f1,
            'tp': tp,
            'fp': fp,
            'fn': fn,
            'tn': tn,
            'question_answered_correctly_rate': answered_correctly / (total) if total > 0 else 0
        })

    # Sort data by F1 score in descending order
    sorted_leaderboard = sorted(leaderboard_data, key=lambda x: x['f1'], reverse=True)
    print(sorted_leaderboard)

    return render(request, 'game/leaderboard.html', {'leaderboard_data': sorted_leaderboard})

