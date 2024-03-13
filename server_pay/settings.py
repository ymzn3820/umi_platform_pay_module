"""
Django settings for server_pay project.

Generated by 'django-admin startproject' using Django 4.2.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""
import traceback

import sys
from pathlib import Path

from config import *

# TODO OPENAI 配置
os.environ["OPENAI_API_KEY"] = ""
os.environ["OPENAI_BASE_URL"] = ""


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, os.path.join(BASE_DIR, "apps"))

#
# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-yk__$8f$bn#i%7es464mlxvhjc03axi1!l_l4d0-@p-7xv-gk*"

# SECURITY WARNING: don't run with debug turned on in production!
ALLOWED_HOSTS = ["*"]

# 跨域增加忽略


CORS_ALLOW_CREDENTIALS = True
CORS_ORIGIN_ALLOW_ALL = True
# CORS_ALLOW_HEADERS = ('*','Content-Type','Fetch-Mode','accept')
CORS_ALLOW_HEADERS = (
    "accept",
    "XMLHttpRequest",
    "X_FILENAME",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "Pragma",
    "token",
    "proxytag",
    "distributed_id_generator",
    "source",
    "role",
    "*",
)
CORS_ALLOW_METHODS = "*"
CORS_ORIGIN_WHITELIST = ()

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "sp_pay",
    # 'sp_pay.apps.SpPayConfig',
    "corsheaders",
    "drf_yasg",
    "rest_framework",
    "gunicorn",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    # 'utils.middlewares.validate_params_middleware.ValidateParamsMiddleware',
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # trace 链路追踪
]

ROOT_URLCONF = "server_pay.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "server_pay.wsgi.application"

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

# LANGUAGE_CODE = 'en-us'

# TIME_ZONE = 'UTC'
LANGUAGE_CODE = "zh-hans"

TIME_ZONE = "Asia/Shanghai"

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = "static/"
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


REST_FRAMEWORK = {
    # 异常处理
    "EXCEPTION_HANDLER": "utils.exception.exception_handler",
    # 'UNAUTHENTICATED_USER': None,
    # 'UNAUTHENTICATED_TOKEN': None,  #将匿名用户设置为None
    # "DEFAULT_AUTHENTICATION_CLASSES": [
    #     "su_user.authorations.EcoAuthentication",
    # ],
    # 'DEFAULT_PERMISSION_CLASSES': [
    #     "utils.permissions.IsLoginUser", #设置路径，
    # ]
}

# 初始化向量数据库
import urllib3
from urllib3.exceptions import InsecureRequestWarning
# 屏蔽 InsecureRequestWarning
urllib3.disable_warnings(InsecureRequestWarning)

from knowledge_base.embedchain.pipeline import Pipeline

try:
    APP = Pipeline.from_config(config_path="opensearch.yaml")
except Exception as e:
    print(traceback.format_exc())