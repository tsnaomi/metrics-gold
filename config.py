import os

from datetime import timedelta

SECRET_KEY = os.getenv('SECRET_KEY', '31415926535')
TESTING = not bool(os.environ.get('DATABASE_URL'))
PERMANENT_SESSION_LIFETIME = timedelta(hours=10)

SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'postgresql:///metric-gold')  # noqa
SQLALCHEMY_TRACK_MODIFICATIONS = False

MAIL_USERNAME = os.getenv('MAIL_USERNAME')
MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
MAIL_DEFAULT_SENDER = ('Metric Gold', os.getenv('MAIL_DEFAULT_SENDER'))
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 465
MAIL_USE_SSL = True
MAIL_SUPPRESS_SEND = False
