from django.urls import path
from . import views

urlpatterns = [
    path('evaluation/', views.evaluation_game_room, name='evaluation_game_room'),
    # path('<str:label>/', views.game_room, name='game_room'),
]
