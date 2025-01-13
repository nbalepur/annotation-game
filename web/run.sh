#!/bin/bash

# Run the server with the --insecure flag
python manage.py collectstatic
uvicorn quizbowl.asgi:application --host 0.0.0.0 --port 8000