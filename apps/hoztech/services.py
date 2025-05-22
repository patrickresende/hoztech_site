import json
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

class NotificationService:
    @staticmethod
    def send_email_notification(subject, template_name, context, recipient_list):
        """
        Envia e-mail usando o Gmail
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
        
        return {
            'email': {'success': email_success, 'message': email_message}
        } 