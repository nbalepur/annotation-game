from django.shortcuts import render
from .models import *

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
