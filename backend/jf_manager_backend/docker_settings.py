from jf_manager_backend.settings import *
import dj_database_url
import environ
import os


env = environ.Env(
    # set casting, default value
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(str, 'localhost'),
    MEDIA_URL=(str, '/uploads/'),
    MEDIA_ROOT=(str, '/app/uploads'),
    CACHE_TTL=(int, 1),
    DEFAULT_FROM_EMAIL=(str, 'webmaster@localhost'),
    EMAIL_HOST=(str, ''),
    EMAIL_PORT=(int, 587),
    EMAIL_HOST_USER=(str, ''),
    EMAIL_HOST_PASSWORD=(str, ''),
    EMAIL_USE_TLS=(bool, True),
    EMAIL_USE_SSL=(bool, False),
    REDIS_URL=(str, 'none'),
)
# Set the project base directory

# Take environment variables from .env file
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

## Expected static files and media URLS --> Docker volumes will be mounted to this directory
STATIC_ROOT = env('STATIC_ROOT')
MEDIA_ROOT = env('MEDIA_ROOT')
MEDIA_URL = env('MEDIA_URL')
MEMBER_UPLOAD_FOLDER = env('MEMBER_UPLOAD_FOLDER', default='members/avatars')
DEBUG = env('DEBUG')
# Raises Django's ImproperlyConfigured
# exception if SECRET_KEY not in os.environ
SECRET_KEY = env('DJANGO_SECRET_KEY')
DATABASE_URL = env('DATABASE_URL', default='sqlite:///db.sqlite3')

ALLOWED_HOSTS = env('ALLOWED_HOSTS').split(',')

DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL')

# Email settings from environment variables
EMAIL_HOST = env('EMAIL_HOST')
EMAIL_PORT = env('EMAIL_PORT')
EMAIL_HOST_USER = env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')
EMAIL_USE_TLS = env('EMAIL_USE_TLS')
EMAIL_USE_SSL = env('EMAIL_USE_SSL')

CACHE_TTL = env('CACHE_TTL')

REDIS_URL = env('REDIS_URL', default='none')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

if REDIS_URL != "none":
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient"
            },
            "KEY_PREFIX": "jf_manager_backend"
        }
    }

if DATABASE_URL != "none":
    DATABASES['default'] = dj_database_url.parse(DATABASE_URL, conn_max_age=600)