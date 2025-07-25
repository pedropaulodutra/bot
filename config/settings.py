import os
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv

# Caminho base do projeto
BASE_DIR = Path(__file__).resolve().parent.parent

# Carrega as variáveis de ambiente de um arquivo .env (útil para desenvolvimento local)
load_dotenv(os.path.join(BASE_DIR, '.env'))

# --- CONFIGURAÇÕES DE SEGURANÇA E AMBIENTE ---

# A SECRET_KEY é lida do ambiente. NUNCA deixe a chave de produção no código.
SECRET_KEY = os.environ.get('SECRET_KEY')

# Detecta se estamos em produção (no Render) ou em desenvolvimento local
# A variável 'RENDER' é fornecida automaticamente pelo Render.
IS_PRODUCTION = 'RENDER' in os.environ
DEBUG = not IS_PRODUCTION

# Hosts permitidos. Em produção, usa o domínio fornecido pelo Render.
ALLOWED_HOSTS = ['localhost', '127.0.0.1']
if IS_PRODUCTION:
    RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
    if RENDER_EXTERNAL_HOSTNAME:
        ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)


# --- APLICAÇÕES E MIDDLEWARE ---

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic', # Whitenoise para arquivos estáticos
    'django.contrib.staticfiles',
    'bot.apps.BotConfig', # Usando a forma explícita
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # Middleware do Whitenoise
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# --- BANCO DE DADOS (PostgreSQL em produção, SQLite localmente) ---

DATABASES = {
    'default': dj_database_url.config(
        # Usa a variável DATABASE_URL em produção, ou um arquivo sqlite3 como padrão local.
        default=f'sqlite:///{BASE_DIR / "db.sqlite3"}',
        conn_max_age=600 # Mantém a conexão viva por 10 minutos
    )
}

# --- SENHAS E AUTENTICAÇÃO ---

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# --- INTERNACIONALIZAÇÃO ---

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

# --- ARQUIVOS ESTÁTICOS (configurados para Whitenoise) ---

STATIC_URL = '/static/'
# Onde o `collectstatic` vai juntar todos os arquivos para o deploy.
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# --- OUTRAS CONFIGURAÇÕES ---

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_REDIRECT_URL = '/bot/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# --- CELERY (lendo a URL do Redis do ambiente) ---

CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'

# --- SEGURANÇA ADICIONAL PARA PRODUÇÃO ---
if IS_PRODUCTION:
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https') # Para confiar no proxy do Render
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True