from datetime import timedelta
from os import getenv


TESTING = not bool(getenv('SECRET_KEY'))
SECRET_KEY = getenv('SECRET_KEY', '31415926535')
PERMANENT_SESSION_LIFETIME = timedelta(hours=10)
ONLINE_LAST_MINUTES = 20

SQLALCHEMY_DATABASE_URI = getenv('DATABASE_URL', 'postgresql:///metric-gold')
SQLALCHEMY_TRACK_MODIFICATIONS = False

MAIL_USERNAME = getenv('MAIL_USERNAME')
MAIL_PASSWORD = getenv('MAIL_PASSWORD')
MAIL_DEFAULT_SENDER = ('Metric Gold', getenv('MAIL_DEFAULT_SENDER'))
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 465
MAIL_USE_SSL = True
MAIL_SUPPRESS_SEND = False
