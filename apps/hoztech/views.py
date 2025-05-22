from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.http import JsonResponse, HttpResponse
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
#import requests
import json
import re
import logging
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt
from .models import CookiePreference
from django.core.serializers import serialize
from django.db.models import Q
from datetime import datetime, timedelta
from .services import NotificationService
import requests

logger = logging.getLogger(__name__)

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def get_ip_location(ip):
    try:
        # Usando o serviço ipapi.co para obter a localização
        response = requests.get(f'https://ipapi.co/{ip}/json/')
        if response.status_code == 200:
            data = response.json()
            location = f"{data.get('city', '')}, {data.get('country_name', '')}"
            return location
    except:
        pass
    return "Localização desconhecida"

def home(request):
    client_ip = get_client_ip(request)
    client_location = get_ip_location(client_ip)
    
    context = {
        'client_ip': client_ip,
        'client_location': client_location
    }
    return render(request, 'hoztech/home.html', context)

def send_whatsapp_message(message):
    """Envia mensagem via WhatsApp Business API"""
    if not all([settings.WHATSAPP_TOKEN, settings.WHATSAPP_PHONE_NUMBER_ID, settings.WHATSAPP_RECIPIENT_NUMBER]):
        logger.error("Configurações do WhatsApp incompletas")
        return False
        
    if not message or len(message.strip()) == 0:
        logger.error("Mensagem vazia")
        return False
        
    try:
        url = f"https://graph.facebook.com/v17.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
        
        headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
            "Content-Type": "application/json"
        }
        
        data = {
            "messaging_product": "whatsapp",
            "to": settings.WHATSAPP_RECIPIENT_NUMBER,
            "type": "text",
            "text": {"body": message}
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        
        response_data = response.json()
        if 'messages' in response_data and response_data['messages'][0].get('id'):
            logger.info(f"Mensagem WhatsApp enviada com sucesso. ID: {response_data['messages'][0]['id']}")
            return True
        else:
            logger.error(f"Resposta inesperada da API do WhatsApp: {response_data}")
            return False
            
    except requests.exceptions.Timeout:
        logger.error("Timeout ao enviar mensagem WhatsApp")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro na requisição WhatsApp: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Erro inesperado ao enviar mensagem WhatsApp: {str(e)}")
        return False

def contato(request):
    if request.method == 'POST':
        # Verifica se é uma requisição AJAX
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        try:
            # Obtém e limpa os dados do formulário
            nome = request.POST.get('nome', '').strip()
            telefone = request.POST.get('telefone', '').strip()
            email = request.POST.get('email', '').strip().lower()  # Converte para minúsculas
            assunto = request.POST.get('assunto', '').strip()
            
            # Validações
            errors = []
            
            # Validação do nome (permitindo acentos e espaços)
            if not re.match(r'^[A-Za-zÀ-ÿ\s]{3,100}$', nome):
                errors.append('Nome inválido. Use apenas letras e espaços (3-100 caracteres).')
            
            # Validação do telefone (formato brasileiro)
            telefone_limpo = re.sub(r'\D', '', telefone)  # Remove não-dígitos
            if not re.match(r'^\d{11}$', telefone_limpo):
                errors.append('Telefone inválido. Use o formato (00) 00000-0000.')
            
            # Validação do email
            try:
                validate_email(email)
                # Verifica se o domínio do email é válido
                domain = email.split('@')[1]
                if not re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', domain):
                    errors.append('Domínio de email inválido.')
            except ValidationError:
                errors.append('Email inválido.')
            
            # Validação do assunto
            if not assunto:
                errors.append('O campo mensagem é obrigatório.')
            elif len(assunto) > 1000:
                errors.append('Mensagem muito longa. Máximo de 1000 caracteres.')
            elif len(assunto) < 10:
                errors.append('Mensagem muito curta. Mínimo de 10 caracteres.')
            
            if errors:
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'message': '\n'.join(errors)
                    })
                for error in errors:
                    messages.error(request, error)
                return redirect('contato')
            
            # Prepara a mensagem
            mensagem = f"""
            🚀 Nova mensagem de contato recebida!
            
            👤 Nome: {nome}
            📱 Telefone: {telefone}
            📧 Email: {email}
            
            💬 Mensagem:
            {assunto}
            
            ⏰ Data/Hora: {timezone.localtime().strftime('%d/%m/%Y %H:%M:%S')}
            """
            
            # Tenta enviar por email
            try:
                email_sent = send_mail(
                    subject=f'Nova mensagem de contato de {nome}',
                    message=mensagem,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.DEFAULT_FROM_EMAIL],
                    fail_silently=False,
                )
            except Exception as e:
                logger.error(f"Erro ao enviar email: {str(e)}")
                email_sent = False
            
            if not email_sent:
                raise Exception("Falha no envio da mensagem por e-mail")
            
            # Log do sucesso
            logger.info(f"Mensagem enviada com sucesso - Email: {email_sent}")
            
            # Resposta de sucesso
            success_message = 'Mensagem enviada com sucesso! Entraremos em contato em breve.'
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': success_message
                })
            
            messages.success(request, success_message)
            return redirect('contato')
            
        except Exception as e:
            logger.error(f"Erro ao processar formulário de contato: {str(e)}")
            error_message = 'Erro ao enviar mensagem. Por favor, tente novamente.'
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': error_message
                })
            messages.error(request, error_message)
            return redirect('contato')
    
    return render(request, 'hoztech/contato.html')

def privacy_modal(request):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'hoztech/privacy_content.html')
    return render(request, 'hoztech/privacy.html')

@csrf_exempt
@require_http_methods(["POST"])
def update_cookie_preferences(request):
    try:
        data = json.loads(request.body)
        client_id = data.get('client_id')
        
        # Tenta encontrar preferências existentes
        try:
            cookie_pref = CookiePreference.objects.get(client_id=client_id)
        except CookiePreference.DoesNotExist:
            # Cria novas preferências se não existirem
            cookie_pref = CookiePreference(client_id=client_id)
        
        # Atualiza as preferências
        preferences = {
            'performance': data.get('performance', True),
            'marketing': data.get('marketing', True)
        }
        
        cookie_pref.update_preferences(preferences, request)
        
        return JsonResponse({
            'status': 'success',
            'message': 'Preferências atualizadas com sucesso',
            'client_id': str(cookie_pref.client_id)
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)

@require_http_methods(["GET"])
def get_cookie_preferences(request, client_id):
    try:
        cookie_pref = CookiePreference.objects.get(client_id=client_id)
        return JsonResponse({
            'status': 'success',
            'preferences': {
                'essential': cookie_pref.essential_cookies,
                'performance': cookie_pref.performance_cookies,
                'marketing': cookie_pref.marketing_cookies,
                'last_updated': cookie_pref.last_updated.isoformat()
            }
        })
    except CookiePreference.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Preferências não encontradas'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)

@require_http_methods(["GET"])
def export_cookie_preferences(request):
    try:
        # Parâmetros de filtro da query string
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        device_type = request.GET.get('device_type')
        browser = request.GET.get('browser')
        country = request.GET.get('country')
        performance = request.GET.get('performance')
        marketing = request.GET.get('marketing')
        
        # Inicia a query
        query = CookiePreference.objects.all()
        
        # Aplica filtros
        if start_date:
            query = query.filter(last_visit__gte=start_date)
        if end_date:
            query = query.filter(last_visit__lte=end_date)
        if device_type:
            query = query.filter(device_type=device_type)
        if browser:
            query = query.filter(browser__icontains=browser)
        if country:
            query = query.filter(country=country)
        if performance is not None:
            query = query.filter(performance_cookies=performance.lower() == 'true')
        if marketing is not None:
            query = query.filter(marketing_cookies=marketing.lower() == 'true')
        
        # Prepara os dados para exportação
        export_data = []
        for pref in query:
            export_data.append({
                'client_id': str(pref.client_id),
                'browser': pref.browser,
                'os': pref.os,
                'device_type': pref.device_type,
                'country': pref.country,
                'city': pref.city,
                'ip_address': pref.ip_address,
                'preferences': {
                    'essential': pref.essential_cookies,
                    'performance': pref.performance_cookies,
                    'marketing': pref.marketing_cookies
                },
                'first_visit': pref.first_visit.isoformat(),
                'last_visit': pref.last_visit.isoformat(),
                'last_updated': pref.last_updated.isoformat(),
                'change_history': pref.change_history
            })
        
        # Gera nome do arquivo com timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'cookie_preferences_{timestamp}.json'
        
        # Prepara a resposta
        response = HttpResponse(
            json.dumps(export_data, indent=2, ensure_ascii=False),
            content_type='application/json'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)

@csrf_exempt
@require_POST
def contact_form(request):
    """
    View para processar o formulário de contato
    """
    try:
        # Obtém os dados do formulário
        form_data = {
            'name': request.POST.get('name', '').strip(),
            'email': request.POST.get('email', '').strip(),
            'phone': request.POST.get('phone', '').strip(),
            'subject': request.POST.get('subject', '').strip(),
            'message': request.POST.get('message', '').strip(),
        }
        
        # Validação básica
        if not all([form_data['name'], form_data['email'], form_data['message']]):
            return JsonResponse({
                'success': False,
                'message': 'Por favor, preencha todos os campos obrigatórios.'
            })
        
        # Envia as notificações
        result = NotificationService.notify_contact_form(form_data)
        
        # Verifica se pelo menos uma notificação foi enviada com sucesso
        if result['email']['success'] or result['whatsapp']['success']:
            return JsonResponse({
                'success': True,
                'message': 'Mensagem enviada com sucesso! Entraremos em contato em breve.',
                'details': result
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Não foi possível enviar a mensagem. Por favor, tente novamente mais tarde.',
                'details': result
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Ocorreu um erro ao processar sua mensagem. Por favor, tente novamente mais tarde.',
            'error': str(e)
        })

# Create your views here.
