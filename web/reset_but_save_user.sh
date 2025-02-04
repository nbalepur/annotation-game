#!/bin/bash

# Checkpoint the user + document data
# python manage.py dumpdata game.User --indent 2 > fixtures/game_user_data.json
# python manage.py dumpdata auth.User --indent 2 > fixtures/auth_user_data.json
# python manage.py dumpdata game.Document --indent 2 > fixtures/document_data.json

# Flush the database
python manage.py flush

# Load the last checkpoint data
python manage.py loaddata fixtures/question_fixtures.json
python manage.py loaddata fixtures/sanity_tutorial_questions.json
python manage.py loaddata fixtures/game_user_data.json
python manage.py loaddata fixtures/auth_user_data.json
python manage.py loaddata fixtures/document_data.json

python manage.py runserver --insecure