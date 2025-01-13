#!/bin/bash

# Run the server with the --insecure flag
python manage.py collectstatic
python manage.py runserver --insecure