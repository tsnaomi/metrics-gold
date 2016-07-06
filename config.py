import os

from datetime import timedelta

PERMANENT_SESSION_LIFETIME = timedelta(hours=10)
SECRET_KEY = os.getenv('SECRET_KEY', '31415926535')
SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'postgresql:///metric-gold')  # noqa
SQLALCHEMY_TRACK_MODIFICATIONS = False
TESTING = not bool(os.environ.get('DATABASE_URL'))
