"""Configurações base do projeto Finance Agent (MVP)."""
import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-inseguro-desenvolvimento"
DEBUG = True
ALLOWED_HOSTS: list[str] = []

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts.apps.AccountsConfig",
    "imports.apps.ImportsConfig",
    "transactions.apps.TransactionsConfig",
    "classification.apps.ClassificationConfig",
    "reports.apps.ReportsConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "finance_agent.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "finance_agent.wsgi.application"
ASGI_APPLICATION = "finance_agent.asgi.application"

tipo_banco = os.getenv("TIPO_BANCO", "sqlite").strip().lower()

if tipo_banco == "postgres":
    postgres_banco = os.getenv("POSTGRES_BANCO")
    postgres_usuario = os.getenv("POSTGRES_USUARIO")
    postgres_senha = os.getenv("POSTGRES_SENHA")
    missing_postgres_vars = [
        var_name
        for var_name, var_value in (
            ("POSTGRES_BANCO", postgres_banco),
            ("POSTGRES_USUARIO", postgres_usuario),
            ("POSTGRES_SENHA", postgres_senha),
        )
        if not var_value
    ]
    if missing_postgres_vars:
        raise ImproperlyConfigured(
            "TIPO_BANCO=postgres requer variáveis obrigatórias: "
            + ", ".join(missing_postgres_vars)
        )

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": postgres_banco,
            "USER": postgres_usuario,
            "PASSWORD": postgres_senha,
            "HOST": os.getenv("POSTGRES_HOST", "localhost"),
            "PORT": os.getenv("POSTGRES_PORTA", "5432"),
        }
    }
elif tipo_banco == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    raise ImproperlyConfigured(
        "TIPO_BANCO inválido. Use 'sqlite' ou 'postgres'. "
        f"Valor recebido: '{tipo_banco}'."
    )

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Configuração explícita de aliases do titular para detectar transferência interna.
# Estrutura:
# {
#   "padrao": ["nome sobrenome"],
#   "por_conta": {
#       "<external_ref_ou_id_da_conta>": ["nome titular", "apelido titular"]
#   }
# }
CLASSIFICACAO_ALIASES_TITULAR = {
    "padrao": [],
    "por_conta": {},
}
