import pytest

from .models import *
from django.core.management import call_command


@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():

        # === Questions ===
        Question.objects.create(
            pk=1,
            category="Literature",
            content="Test content",
            answer="Test answer",
            difficulty="HS",
        )

        # === Rooms ===
        testroom = Room.objects.create(
            label='testroom',
        )
        testroom2 = Room.objects.create(
            label='testroom2',
        )

        # === Users ===
        user_chad = User.objects.create(
            user_id=1,
            name="chad"
        )
        user_vivian = User.objects.create(
            user_id=2,
            name="vivian",
        )
        user_jesus = User.objects.create(
            user_id=3,
            name="jesus",
        )

        # === Players ===
        player_1 = Player.objects.create(
            user=user_chad,
            room=testroom,
            last_seen=datetime.datetime.now().timestamp(),
        )

        player_2 = Player.objects.create(
            user=user_vivian,
            room=testroom,
        )

        player_3 = Player.objects.create(
            user=user_jesus,
            room=testroom,
            banned=True,
        )
        player_3.reported_by.add(player_1)
        player_3.reported_by.add(player_2)

        player_4 = Player.objects.create(
            user=user_jesus,
            room=testroom2,
        )
