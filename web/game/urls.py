from django.urls import path
from . import views
from .views import oauth_login, oauth_callback, profile

urlpatterns = [
    path('evaluation/<str:label>/', views.evaluation_game_room, name='evaluation_game_room'),
    path('oauth/login/', oauth_login, name='oauth_login'),
    path('oauth/callback/', oauth_callback, name='oauth_callback'),
    path('profile/', profile, name='profile'),
    path('test-session/', views.test_session, name='test_session'),  # Redirect here after successful login
    # path('<str:label>/', views.game_room, name='game_room'),
]
