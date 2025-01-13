#!/bin/bash

# Save the user data
#python manage.py dumpdata game.User --indent 2 > fixtures/game_user_data.json
#python manage.py dumpdata auth.User --indent 2 > fixtures/auth_user_data.json

# Flush the database
python manage.py flush

# Load the fixture data
python manage.py loaddata fixtures/question_fixtures.json
python manage.py loaddata fixtures/sanity_tutorial_questions.json
python manage.py loaddata fixtures/game_user_data.json
python manage.py loaddata fixtures/auth_user_data.json

gunicorn myproject.wsgi:application --bind 0.0.0.0:8000