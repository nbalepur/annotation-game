import random
import html
import datetime
import uuid
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv
load_dotenv()

PREFIX = [
    "scarred",
    "light",
    "lost",
    "jelly",
    "cursed",
    "latent",
    "fake",
    "immortal",
]

NOUNS = [
    "vampire",
    "crab",
    "snail",
    "monkey",
    "snake",
    "cat",
    "bee",
    "phoenix",
]


def clean_content(content):
    """Escapes HTML
    """
    return html.escape(content)


def generate_name():
    """Generates randomized name
    """
    return '-'.join([random.choice(PREFIX), random.choice(NOUNS)])


def generate_id():
    """Generate user id
    """
    # TODO: account for collision??
    return uuid.uuid4().hex

def send_email(to_email, subject, message):
    message = Mail(
        from_email=os.getenv('EMAIL'),
        to_emails=to_email,
        subject=subject,
        html_content=message)
    sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
    response = sg.send(message)
    return response