import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Minimal settings for local development
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'dev-secret-key')
DEBUG = True
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
	'django.contrib.auth',
	'django.contrib.contenttypes',
	'django.contrib.sessions',
	'django.contrib.messages',
	'django.contrib.staticfiles',
	'rest_framework',
	'chatbot',
	'hotels',
]

MIDDLEWARE = [
	'django.middleware.security.SecurityMiddleware',
	'django.contrib.sessions.middleware.SessionMiddleware',
	'django.middleware.common.CommonMiddleware',
	'django.middleware.csrf.CsrfViewMiddleware',
	'django.contrib.auth.middleware.AuthenticationMiddleware',
	'django.contrib.messages.middleware.MessageMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
	{
		'BACKEND': 'django.template.backends.django.DjangoTemplates',
		'DIRS': [str(BASE_DIR / 'frontend' / 'templates')],
		'APP_DIRS': True,
		'OPTIONS': {'context_processors': []},
	}
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
	'default': {
		'ENGINE': 'django.db.backends.sqlite3',
		'NAME': str(BASE_DIR / 'db.sqlite3'),
	}
}

STATIC_URL = '/static/'
STATICFILES_DIRS = [str(BASE_DIR / 'frontend' / 'static')]

# Simple logging to console
LOGGING = {
	'version': 1,
	'disable_existing_loggers': False,
	'handlers': {'console': {'class': 'logging.StreamHandler'}},
	'root': {'handlers': ['console'], 'level': 'INFO'},
}
