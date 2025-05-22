import json
import requests
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

class NotificationService:
    @staticmethod
    def send_email_notification(subject, template_name, context, recipient_list):
        """
        Envia e-mail usando o Proton Mail
        """
        try:
            # Renderiza o template HTML
            html_message = render_to_string(f'hoztech/emails/{template_name}.html', context)
            plain_message = strip_tags(html_message)
            
            # Envia o e-mail
            send_mail(
                subject=f"{settings.EMAIL_SUBJECT_PREFIX}{subject}",
                message=plain_message,
                html_message=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipient_list,
                fail_silently=False,
            )
            return True, "E-mail enviado com sucesso"
        except Exception as e:
            return False, f"Erro ao enviar e-mail: {str(e)}"

    @staticmethod
    def send_whatsapp_message(phone_number, message):
        """
        Envia mensagem via WhatsApp Business API
        """
        try:
            headers = {
                'Authorization': f'Bearer {settings.WHATSAPP_TOKEN}',
                'Content-Type': 'application/json',
            }
            
            data = {
                "messaging_product": "whatsapp",
                "to": phone_number,
                "type": "text",
                "text": {"body": message}
            }
            
            response = requests.post(
                settings.WHATSAPP_API_URL,
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                return True, "Mensagem WhatsApp enviada com sucesso"
            else:
                return False, f"Erro ao enviar WhatsApp: {response.text}"
                
        except Exception as e:
            return False, f"Erro ao enviar WhatsApp: {str(e)}"

    @classmethod
    def notify_contact_form(cls, form_data):
        """
        Processa o formulário de contato e envia notificações
        """
        # Prepara o contexto para o template
        context = {
            'name': form_data.get('name'),
            'email': form_data.get('email'),
            'phone': form_data.get('phone'),
            'message': form_data.get('message'),
            'subject': form_data.get('subject', 'Novo contato via site'),
        }
        
        # Envia e-mail
        email_success, email_message = cls.send_email_notification(
            subject=context['subject'],
            template_name='contact_form',
            context=context,
            recipient_list=[settings.DEFAULT_FROM_EMAIL]
        )
        
        # Envia WhatsApp se o número estiver disponível
        whatsapp_success = True
        whatsapp_message = "WhatsApp não enviado (sem número)"
        
        if form_data.get('phone'):
            # Formata o número para o padrão internacional
            phone = form_data['phone'].replace('(', '').replace(')', '').replace('-', '').replace(' ', '')
            if not phone.startswith('55'):  # Adiciona código do Brasil se necessário
                phone = f"55{phone}"
            
            # Prepara a mensagem do WhatsApp
            whatsapp_text = f"""
*Novo contato via site Hoztech*

Nome: {context['name']}
E-mail: {context['email']}
Telefone: {context['phone']}
Assunto: {context['subject']}

Mensagem:
{context['message']}
"""
            whatsapp_success, whatsapp_message = cls.send_whatsapp_message(phone, whatsapp_text)
        
        return {
            'email': {'success': email_success, 'message': email_message},
            'whatsapp': {'success': whatsapp_success, 'message': whatsapp_message}
        } 