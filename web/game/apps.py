from django.apps import AppConfig
from django.conf import settings

class GameConfig(AppConfig):
    name = 'game'
    verbose_name = "Annotation Game"

    def ready(self):
        from .tasks import send_next_question
        send_next_question.delay()