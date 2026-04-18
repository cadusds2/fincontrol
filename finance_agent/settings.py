"""Configurações base do projeto Finance Agent (MVP)."""
import os
from pathlib import Path
from urllib.parse import parse_qsl, urlparse
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def carregar_dotenv(caminho_arquivo: Path) -> None:
    """Carrega variáveis simples de um arquivo .env sem dependências externas."""
    if not caminho_arquivo.exists():
        return

    for linha in caminho_arquivo.read_text(encoding="utf-8").splitlines():
        conteudo = linha.strip()
        if not conteudo or conteudo.startswith("#") or "=" not in conteudo:
            continue

        chave, valor = conteudo.split("=", 1)
        chave = chave.strip()
        valor = valor.strip().strip("'\"")

        if chave:
            os.environ.setdefault(chave, valor)


carregar_dotenv(BASE_DIR / ".env")

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

uri_banco_dados = (os.getenv("DATABASE_URI") or "").strip()

if not uri_banco_dados:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    uri_parseada = urlparse(uri_banco_dados)

    if uri_parseada.scheme not in {"postgres", "postgresql"}:
        raise ImproperlyConfigured(
            "DATABASE_URI inválida. Use URI PostgreSQL com esquema 'postgres://' "
            "ou 'postgresql://'."
        )

    nome_banco = uri_parseada.path.lstrip("/")
    if not nome_banco:
        raise ImproperlyConfigured(
            "DATABASE_URI inválida: o nome do banco deve estar presente no caminho."
        )

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": nome_banco,
            "USER": uri_parseada.username or "",
            "PASSWORD": uri_parseada.password or "",
            "HOST": uri_parseada.hostname or "",
            "PORT": str(uri_parseada.port or ""),
        }
    }

    parametros_consulta = dict(parse_qsl(uri_parseada.query, keep_blank_values=True))
    if parametros_consulta:
        DATABASES["default"]["OPTIONS"] = parametros_consulta

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

CLASSIFICACAO_FUZZY_AUTO_THRESHOLD = 90
CLASSIFICACAO_FUZZY_REVIEW_THRESHOLD = 80
