FROM python:3.11.7-slim

# Update package lists and install necessary packages
RUN apt-get update
RUN apt-get install -y \
    postgresql-client \
    postgresql-server-dev-all \
    gcc \
    python3-dev \
    libmusl-dev \
    libffi-dev \
    bash \
    automake \
    g++ \
    subversion

# Upgrade pip
RUN python3 -m pip install --upgrade pip

# Set the working directory inside the container
WORKDIR /usr/src/app

# Copy requirements file to the working directory
COPY requirements.txt requirements.txt

# Install Python dependencies from the requirements file
RUN python3 -m pip install -r requirements.txt

# Copy the current directory contents into the container at /usr/src/app
COPY . .