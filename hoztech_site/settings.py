import re

# Configurações do WhatsApp Business API
WHATSAPP_TOKEN = 'YOUR_WHATSAPP_TOKEN'  # Substitua pelo seu token
WHATSAPP_PHONE_NUMBER_ID = 'YOUR_PHONE_NUMBER_ID'  # Substitua pelo seu Phone Number ID
WHATSAPP_BUSINESS_ACCOUNT_ID = 'YOUR_BUSINESS_ACCOUNT_ID'  # Substitua pelo seu Business Account ID
WHATSAPP_RECIPIENT_NUMBER = '5521973007575'  # Seu número do WhatsApp (formato internacional sem + ou espaços)

# Validação do número do WhatsApp
if not re.match(r'^\d{13}$', WHATSAPP_RECIPIENT_NUMBER):
    raise ValueError('WHATSAPP_RECIPIENT_NUMBER deve estar no formato internacional (ex: 5521973007575)') 