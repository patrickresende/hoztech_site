import re
import os

# Configurações do WhatsApp Business API
WHATSAPP_TOKEN = 'YOUR_WHATSAPP_TOKEN'  # Substitua pelo seu token
WHATSAPP_PHONE_NUMBER_ID = 'YOUR_PHONE_NUMBER_ID'  # Substitua pelo seu Phone Number ID
WHATSAPP_BUSINESS_ACCOUNT_ID = 'YOUR_BUSINESS_ACCOUNT_ID'  # Substitua pelo seu Business Account ID
WHATSAPP_RECIPIENT_NUMBER = '5521973007575'  # Seu número do WhatsApp (formato internacional sem + ou espaços)

# Validação do número do WhatsApp
if not re.match(r'^\d{13}$', WHATSAPP_RECIPIENT_NUMBER):
    raise ValueError('WHATSAPP_RECIPIENT_NUMBER deve estar no formato internacional (ex: 5521973007575)')

# Configurações de E-mail
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@hoztech.com.br')
TEAM_NOTIFICATION_EMAIL = os.getenv('TEAM_NOTIFICATION_EMAIL', 'equipe@hoztech.com.br')

# Configurações de Mídia
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Configurações de Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'error.log'),
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'hoztech': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'hoztech.middleware.VisitorTrackingMiddleware',  # Adiciona o middleware de rastreamento
] 