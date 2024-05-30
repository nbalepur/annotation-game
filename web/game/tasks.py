# from demoapp.models import Widget

import asyncio
import time
from typing import List
from celery import shared_task
from channels.layers import get_channel_layer
from channels.db import database_sync_to_async as to_async

channel_layer = get_channel_layer()

from .models import Room
from asgiref.sync import async_to_sync



@shared_task
def send_next_question():
    while True:
        # Fetch all rooms in 'playing' or 'contest' state
        rooms = Room.objects.filter(state__in=[Room.GameState.PLAYING, Room.GameState.CONTEST])
        
        for room in rooms:
            room_group_name = f"game-{room.label}"
            get_shown_question(room=room, room_group_name=room_group_name)
        
        # Sleep for 100 ms
        time.sleep(0.1)

def get_shown_question(room: Room, room_group_name: str):
    """Computes the correct amount of the question to show, depending on the state of the game."""
    question: str = room.get_shown_question()

    async_to_sync(channel_layer.group_send)(
        room_group_name,
        {
            'type': 'update_room',
            'data': {
                "response_type": "get_shown_question",
                "shown_question": question,
            },
        }
    )