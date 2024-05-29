# from demoapp.models import Widget

import asyncio
import time
from celery import shared_task
from channels.layers import get_channel_layer
from channels.db import database_sync_to_async as to_async

channel_layer = get_channel_layer()

from .models import Room
from asgiref.sync import async_to_sync


@shared_task
def send_next_question(room_label: str, room_group_name: str, interval: float):
    room: Room = Room.objects.get(label=room_label)

    while room.state == Room.GameState.PLAYING:
        get_shown_question(room=room, room_group_name=room_group_name)
        time.sleep(interval)
        room: Room = Room.objects.get(label=room_label)

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