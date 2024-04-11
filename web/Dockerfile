FROM python:3.11.7-alpine

RUN apk update
RUN apk add postgresql-dev postgresql-client gcc python3-dev musl-dev libffi-dev bash

RUN python3 -m pip install --upgrade pip

WORKDIR /usr/src/app

COPY requirements.txt requirements.txt
RUN python3 -m pip install -r requirements.txt

COPY . .