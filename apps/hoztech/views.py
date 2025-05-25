from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.http import JsonResponse, HttpResponse
from django.core.mail import send_mail, EmailMessage
from django.conf import settings
from django.utils import timezone
from django.db.models import Count
#import requests
import json
import re
import logging
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from .models import CookiePreference, PDFDownload
from django.core.serializers import serialize
from django.db.models import Q
from datetime import datetime, timedelta
from .services import NotificationService
from .ip_client import IPClientService
import requests
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login, logout, authenticate
from django.core.paginator import Paginator
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import FileResponse
import csv
import os
from .models import VisitorAccess, CookieConsent, AdminAccessLog, DataExport, AdminAuthImage, AdminUserAuthPreference
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.views.decorators.cache import never_cache
import random
from django.template.loader import render_to_string
from django.core.cache import cache
from django.db.models.functions import ExtractHour
from django.core.management import call_command
from contextlib import redirect_stdout
import io
import time

logger = logging.getLogger(__name__)

def is_admin(user):
    """Verifica se o usuário é um administrador"""
    return user.is_authenticated and user.is_staff

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
    # Obtém informações do cliente usando o novo serviço
    ip, location_data, browser_info, connection_info = IPClientService.get_client_info(request)
    location_string = IPClientService.format_location_string(location_data)
    
    context = {
        'client_ip': ip,
        'client_location': location_string,
        'location_data': location_data,  # Dados completos para uso futuro
        'browser_info': browser_info,    # Informações do navegador
        'connection_info': connection_info  # Informações de conexão
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

@require_http_methods(['POST'])
@csrf_exempt
def update_cookie_preferences(request):
    try:
        data = json.loads(request.body)
        client_id = data.get('client_id')
        preferences = data.get('preferences', {})
        
        # Obtém ou cria o registro de preferências
        cookie_pref, created = CookiePreference.objects.get_or_create(
            client_id=client_id,
            defaults={
                'ip_address': get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'essential_cookies': True,  # Sempre True
                'performance_cookies': preferences.get('performance', False),
                'marketing_cookies': preferences.get('marketing', False)
            }
        )
        
        if not created:
            cookie_pref.performance_cookies = preferences.get('performance', False)
            cookie_pref.marketing_cookies = preferences.get('marketing', False)
            cookie_pref.save()
        
        # Registra os cookies no banco de dados
        visitor = VisitorAccess.objects.filter(
            ip_address=get_client_ip(request),
            session_id=request.session.session_key
        ).order_by('-timestamp').first()
        
        if visitor:
            # Registra cada cookie aceito
            for cookie_name, cookie_data in preferences.items():
                if cookie_data.get('consent'):
                    CookieConsent.objects.create(
                        visitor=visitor,
                        cookie_name=cookie_name,
                        value=cookie_data.get('value', ''),
                        category=cookie_data.get('category', 'essential'),
                        expires_at=timezone.now() + timezone.timedelta(days=365)
                    )
        
        return JsonResponse({
            'status': 'success',
            'message': 'Preferências atualizadas com sucesso',
            'client_id': str(cookie_pref.client_id)
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Dados inválidos'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

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
            # Obtém informações do IP se não existirem
            if not all([pref.browser, pref.os, pref.device_type, pref.country, pref.city]):
                try:
                    # Usa o serviço IPClientService para obter informações
                    ip_info = IPClientService.get_ip_info(pref.ip_address)
                    
                    # Atualiza o registro se necessário
                    if ip_info:
                        pref.browser = ip_info.get('browser', pref.browser)
                        pref.os = ip_info.get('os', pref.os)
                        pref.device_type = ip_info.get('device_type', pref.device_type)
                        pref.country = ip_info.get('country', pref.country)
                        pref.city = ip_info.get('city', pref.city)
                        pref.save()
                except Exception as e:
                    logger.error(f"Erro ao obter informações do IP {pref.ip_address}: {str(e)}")
            
            # Adiciona dados do visitante
            visitor = VisitorAccess.objects.filter(
                ip_address=pref.ip_address,
                timestamp__gte=pref.first_visit,
                timestamp__lte=pref.last_visit
            ).order_by('-timestamp').first()
            
            # Prepara o registro para exportação
            export_record = {
                'client_id': str(pref.client_id),
                'browser': pref.browser or visitor.browser if visitor else None,
                'os': pref.os or visitor.os if visitor else None,
                'device_type': pref.device_type or visitor.device_type if visitor else None,
                'country': pref.country or visitor.country if visitor else None,
                'city': pref.city or visitor.city if visitor else None,
                'ip_address': pref.ip_address,
                'preferences': {
                    'essential': pref.essential_cookies,
                    'performance': pref.performance_cookies,
                    'marketing': pref.marketing_cookies
                },
                'first_visit': pref.first_visit.isoformat(),
                'last_visit': pref.last_visit.isoformat(),
                'last_updated': pref.last_updated.isoformat(),
                'change_history': pref.change_history,
                'visitor_info': {
                    'total_visits': VisitorAccess.objects.filter(ip_address=pref.ip_address).count(),
                    'last_visit_details': {
                        'timestamp': visitor.timestamp.isoformat() if visitor else None,
                        'user_agent': visitor.user_agent if visitor else None,
                        'referrer': visitor.referrer if visitor else None,
                        'page_visited': visitor.page_visited if visitor else None
                    } if visitor else None
                }
            }
            
            # Adiciona estatísticas de consentimento
            consent_stats = CookieConsent.objects.filter(
                visitor__ip_address=pref.ip_address
            ).values('category').annotate(
                count=Count('id')
            )
            export_record['consent_stats'] = {
                stat['category']: stat['count'] for stat in consent_stats
            }
            
            export_data.append(export_record)
        
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
        logger.error(f"Erro na exportação: {str(e)}")
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

class AdminLoginView(LoginView):
    template_name = 'hoztech/admin/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        return reverse_lazy('admin_dashboard')
    
    def form_valid(self, form):
        user = form.get_user()
        auth_pref = user.auth_preference
        
        # Verifica se a conta está bloqueada
        if auth_pref.check_lock_status():
            messages.error(self.request, 'Sua conta está temporariamente bloqueada. Tente novamente mais tarde.')
            return redirect('admin_login')
        
        # Verifica se o IP está permitido
        client_ip = get_client_ip(self.request)
        if not auth_pref.is_ip_allowed(client_ip):
            messages.error(self.request, 'Acesso não permitido deste IP.')
            AdminAccessLog.objects.create(
                user=user,
                ip_address=client_ip,
                action='login_blocked_ip',
                details={'ip': client_ip},
                success=False
            )
            return redirect('admin_login')
        
        # Verifica se é necessário trocar a senha
        if auth_pref.require_password_change:
            messages.warning(self.request, 'É necessário trocar sua senha.')
            return redirect('admin_password_change')
        
        # Faz login e registra o acesso
        login(self.request, user)
        auth_pref.reset_login_attempts()
        
        # Registra o login bem-sucedido
        AdminAccessLog.objects.create(
            user=user,
            ip_address=client_ip,
            action='login_success',
            success=True
        )
        
        # Notifica sobre o login se configurado
        if auth_pref.notify_on_login:
            self._send_login_notification(user, client_ip)
        
        # Redireciona para 2FA se ativado
        if auth_pref.is_2fa_enabled:
            self.request.session['auth_user_id'] = user.id
            self.request.session['auth_username'] = user.username
            return redirect('admin_2fa_verify')
        
        return redirect('admin_dashboard')
    
    def form_invalid(self, form):
        username = form.cleaned_data.get('username')
        client_ip = get_client_ip(self.request)
        
        try:
            user = User.objects.get(username=username)
            auth_pref = user.auth_preference
            auth_pref.increment_login_attempts()
            
            # Registra a tentativa falha
            AdminAccessLog.objects.create(
                user=user,
                ip_address=client_ip,
                action='login_failed',
                details={'username': username},
                success=False
            )
            
            if auth_pref.check_lock_status():
                messages.error(self.request, 'Sua conta foi bloqueada após várias tentativas falhas. Tente novamente em 30 minutos.')
            else:
                attempts_left = 5 - auth_pref.login_attempts
                messages.error(self.request, f'Credenciais inválidas. Tentativas restantes: {attempts_left}')
                
        except User.DoesNotExist:
            # Registra tentativa com usuário inexistente
            AdminAccessLog.objects.create(
                ip_address=client_ip,
                action='login_failed',
                details={'username': username},
                success=False
            )
            messages.error(self.request, 'Credenciais inválidas.')
        
        return super().form_invalid(form)
    
    def _send_login_notification(self, user, ip_address):
        """Envia notificação de login por email"""
        try:
            subject = 'Novo acesso à sua conta administrativa'
            message = render_to_string('hoztech/admin/email/login_notification.html', {
                'user': user,
                'ip_address': ip_address,
                'timestamp': timezone.now(),
                'browser': self.request.user_agent.browser.family,
                'os': self.request.user_agent.os.family,
                'device': self.request.user_agent.device.family,
            })
            
            send_mail(
                subject=subject,
                message=strip_tags(message),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=message,
                fail_silently=True
            )
        except Exception as e:
            logger.error(f"Erro ao enviar notificação de login: {str(e)}")

@method_decorator(never_cache, name='dispatch')
class Admin2FAVerifyView(TemplateView):
    template_name = 'hoztech/admin/2fa_verify.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Verifica se o usuário está no processo de autenticação
        if 'auth_user_id' not in request.session:
            return redirect('admin_login')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_id = self.request.session.get('auth_user_id')
        
        try:
            user = User.objects.get(id=user_id)
            auth_pref = user.auth_preference
            
            if not auth_pref.is_2fa_enabled:
                # Se 2FA está desativado, faz login direto
                login(self.request, user)
                return redirect('admin_dashboard')
            
            # Seleciona imagens aleatórias para verificação
            all_images = AdminAuthImage.objects.filter(is_active=True)
            user_images = auth_pref.auth_images.all()
            
            if not user_images.exists():
                # Se o usuário não tem imagens selecionadas, usa todas as ativas
                user_images = all_images
            
            # Seleciona 3 imagens aleatórias, incluindo a última usada
            selected_images = list(user_images.exclude(id=auth_pref.last_auth_image.id if auth_pref.last_auth_image else None))
            if len(selected_images) < 3:
                # Se não houver imagens suficientes, adiciona outras aleatórias
                other_images = list(all_images.exclude(id__in=[img.id for img in selected_images]))
                selected_images.extend(random.sample(other_images, min(3 - len(selected_images), len(other_images))))
            
            # Adiciona a última imagem usada se existir
            if auth_pref.last_auth_image and auth_pref.last_auth_image.is_active:
                selected_images.append(auth_pref.last_auth_image)
            
            # Embaralha as imagens
            random.shuffle(selected_images)
            selected_images = selected_images[:3]  # Limita a 3 imagens
            
            context['auth_images'] = selected_images
            context['username'] = user.username
            
        except User.DoesNotExist:
            return redirect('admin_login')
        
        return context
    
    def post(self, request, *args, **kwargs):
        user_id = request.session.get('auth_user_id')
        selected_image_id = request.POST.get('selected_image')
        
        try:
            user = User.objects.get(id=user_id)
            auth_pref = user.auth_preference
            selected_image = AdminAuthImage.objects.get(id=selected_image_id)
            
            # Verifica se a imagem selecionada está nas preferências do usuário
            if selected_image in auth_pref.auth_images.all():
                # Atualiza a última imagem usada
                auth_pref.last_auth_image = selected_image
                auth_pref.save()
                
                # Faz login do usuário
                login(request, user)
                
                # Registra o login bem-sucedido
                AdminAccessLog.objects.create(
                    user=user,
                    ip_address=get_client_ip(request),
                    action='login_success',
                    success=True
                )
                
                # Limpa a sessão de autenticação
                request.session.pop('auth_user_id', None)
                request.session.pop('auth_username', None)
                
                return redirect('admin_dashboard')
            else:
                # Registra a tentativa falha
                AdminAccessLog.objects.create(
                    user=user,
                    ip_address=get_client_ip(request),
                    action='2fa_failed',
                    details={'selected_image': str(selected_image_id)},
                    success=False
                )
                messages.error(request, 'Imagem de autenticação inválida.')
                return redirect('admin_2fa_verify')
                
        except (User.DoesNotExist, AdminAuthImage.DoesNotExist):
            return redirect('admin_login')

@login_required
def admin_2fa_settings(request):
    """View para gerenciar configurações 2FA do usuário"""
    if request.method == 'POST':
        action = request.POST.get('action')
        auth_pref = request.user.auth_preference
        
        if action == 'toggle_2fa':
            auth_pref.is_2fa_enabled = not auth_pref.is_2fa_enabled
            auth_pref.save()
            messages.success(request, 'Configurações de autenticação atualizadas.')
            
        elif action == 'update_images':
            selected_images = request.POST.getlist('auth_images')
            auth_pref.auth_images.set(selected_images)
            messages.success(request, 'Imagens de autenticação atualizadas.')
            
        return redirect('admin_2fa_settings')
    
    # Lista todas as imagens disponíveis, agrupadas por categoria
    all_images = AdminAuthImage.objects.filter(is_active=True).order_by('category', 'name')
    categories = {}
    for image in all_images:
        if image.category not in categories:
            categories[image.category] = []
        categories[image.category].append(image)
    
    return render(request, 'hoztech/admin/2fa_settings.html', {
        'categories': categories,
        'selected_images': request.user.auth_preference.auth_images.all(),
        'is_2fa_enabled': request.user.auth_preference.is_2fa_enabled
    })

@method_decorator(never_cache, name='dispatch')
class AdminDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'hoztech/admin/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            # Estatísticas gerais (com cache)
            cache_key = 'dashboard_stats'
            stats = cache.get(cache_key)
            
            if stats is None:
                now = timezone.now()
                last_30_days = now - timedelta(days=30)
                
                # Usa select_related e prefetch_related para otimizar queries
                visitors_30d = VisitorAccess.objects.filter(
                    timestamp__gte=last_30_days
                ).select_related()
                
                stats = {
                    'total_visitors': VisitorAccess.objects.count(),
                    'total_cookies': CookieConsent.objects.count(),
                    'visitors_30d': visitors_30d.count(),
                    'unique_ips_30d': visitors_30d.values('ip_address').distinct().count(),
                    'top_countries': visitors_30d.exclude(
                        country__isnull=True
                    ).values('country').annotate(
                        count=Count('id')
                    ).order_by('-count')[:5],
                    'top_browsers': visitors_30d.exclude(
                        browser__isnull=True
                    ).values('browser').annotate(
                        count=Count('id')
                    ).order_by('-count')[:5],
                }
                
                # Cache por 5 minutos
                cache.set(cache_key, stats, 300)
            
            context.update(stats)
            
            # Visitantes recentes (sem cache)
            context['recent_visitors'] = VisitorAccess.objects.select_related(
            ).order_by('-timestamp')[:10]
            
            # Exportações recentes (sem cache)
            context['recent_exports'] = DataExport.objects.filter(
                user=self.request.user
            ).order_by('-timestamp')[:5]
            
            # Adiciona estatísticas de cookies por categoria
            context['cookie_categories'] = CookieConsent.objects.values(
                'category'
            ).annotate(
                count=Count('id')
            ).order_by('-count')
            
            # Adiciona estatísticas de dispositivos
            context['device_types'] = VisitorAccess.objects.exclude(
                device_type__isnull=True
            ).values('device_type').annotate(
                count=Count('id')
            ).order_by('-count')[:5]
            
            # Adiciona estatísticas de horários de acesso
            context['access_hours'] = VisitorAccess.objects.annotate(
                hour=ExtractHour('timestamp')
            ).values('hour').annotate(
                count=Count('id')
            ).order_by('hour')
            
        except Exception as e:
            logger.error(f"Erro ao carregar dashboard: {str(e)}")
            messages.error(self.request, "Erro ao carregar estatísticas do dashboard")
            
        return context

@login_required
@never_cache
def admin_logout(request):
    AdminAccessLog.objects.create(
        user=request.user,
        ip_address=get_client_ip(request),
        action='logout',
        success=True
    )
    logout(request)
    return redirect('admin_login')

@login_required
@never_cache
def visitor_list(request):
    page = request.GET.get('page', 1)
    ip = request.GET.get('ip', '')
    country = request.GET.get('country', '')
    city = request.GET.get('city', '')
    date = request.GET.get('date', '')

    visitors = VisitorAccess.objects.all()

    if ip:
        visitors = visitors.filter(ip_address__icontains=ip)
    if country:
        visitors = visitors.filter(country__icontains=country)
    if city:
        visitors = visitors.filter(city__icontains=city)
    if date:
        visitors = visitors.filter(timestamp__date=date)

    paginator = Paginator(visitors, 50)
    visitors_page = paginator.get_page(page)

    return render(request, 'hoztech/admin/visitor_list.html', {
        'visitors': visitors_page,
        'ip': ip,
        'country': country,
        'city': city,
        'date': date,
    })

@login_required
@never_cache
def cookie_list(request):
    page = request.GET.get('page', 1)
    search = request.GET.get('search', '')
    category = request.GET.get('category')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    cookies = CookieConsent.objects.select_related('visitor').all()
    
    if search:
        cookies = cookies.filter(
            Q(cookie_name__icontains=search) |
            Q(visitor__ip_address__icontains=search)
        )
    
    if category:
        cookies = cookies.filter(category=category)
    
    if date_from:
        cookies = cookies.filter(timestamp__gte=date_from)
    if date_to:
        cookies = cookies.filter(timestamp__lte=date_to)
    
    paginator = Paginator(cookies, 50)
    cookies_page = paginator.get_page(page)
    
    # Get cookie categories from model choices
    categories = CookieConsent._meta.get_field('category').choices
    
    return render(request, 'hoztech/admin/cookie_list.html', {
        'cookies': cookies_page,
        'search': search,
        'category': category,
        'date_from': date_from,
        'date_to': date_to,
        'categories': categories
    })

@method_decorator(never_cache, name='dispatch')
class AdminExportView(LoginRequiredMixin, TemplateView):
    template_name = 'hoztech/admin/export.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Adiciona dados de contexto se necessário
        return context

@login_required
@user_passes_test(is_admin)
def export_data(request):
    """Exporta dados do sistema em diferentes formatos."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido'}, status=405)
    
    try:
        # Obtém parâmetros da requisição
        export_type = request.POST.get('export_type')
        date_from = request.POST.get('date_from')
        date_to = request.POST.get('date_to')
        format_type = request.POST.get('format', 'json')
        include_headers = request.POST.get('include_headers', 'true') == 'true'
        compress = request.POST.get('compress', 'false') == 'true'
        async_export = request.POST.get('async_export', 'false') == 'true'
        
        # Filtros adicionais
        country = request.POST.get('country')
        device_type = request.POST.get('device_type')
        browser = request.POST.get('browser')
        
        # Validação básica
        if not all([export_type, date_from, date_to]):
            return JsonResponse({'error': 'Parâmetros obrigatórios não fornecidos'}, status=400)
        
        # Converte datas
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'error': 'Formato de data inválido'}, status=400)
        
        # Valida período
        if (date_to - date_from).days > 365:
            return JsonResponse({'error': 'Período máximo de exportação é 365 dias'}, status=400)
        
        # Cria registro de exportação
        export = DataExport.objects.create(
            user=request.user,
            export_type=export_type,
            date_range_start=date_from,
            date_range_end=date_to,
            format=format_type,
            status='processing'
        )
        
        # Se for exportação assíncrona, inicia tarefa em background
        if async_export:
            from .tasks import process_export
            process_export.delay(export.id)
            return JsonResponse({
                'status': 'processing',
                'message': 'Exportação iniciada em background',
                'export_id': export.id
            })
        
        # Processamento síncrono
        try:
            # Prepara query base
            if export_type == 'cookies':
                queryset = CookieConsent.objects.filter(
                    timestamp__date__range=[date_from, date_to]
                )
            elif export_type == 'access':
                queryset = VisitorAccess.objects.filter(
                    timestamp__date__range=[date_from, date_to]
                )
            else:  # all
                queryset = {
                    'cookies': CookieConsent.objects.filter(
                        timestamp__date__range=[date_from, date_to]
                    ),
                    'access': VisitorAccess.objects.filter(
                        timestamp__date__range=[date_from, date_to]
                    )
                }
            
            # Aplica filtros adicionais
            if export_type != 'all':
                if country:
                    queryset = queryset.filter(country=country)
                if device_type:
                    queryset = queryset.filter(device_type=device_type)
                if browser:
                    queryset = queryset.filter(browser=browser)
            
            # Prepara dados para exportação
            if export_type == 'all':
                data = {
                    'cookies': list(queryset['cookies'].values()),
                    'access': list(queryset['access'].values())
                }
            else:
                data = list(queryset.values())
            
            # Gera arquivo
            filename = f"export_{export_type}_{date_from}_{date_to}"
            if format_type == 'json':
                content = json.dumps(data, indent=2, default=str)
                filepath = f"exports/{filename}.json"
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
            elif format_type == 'csv':
                import csv
                filepath = f"exports/{filename}.csv"
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    if export_type == 'all':
                        writer = csv.writer(f)
                        if include_headers:
                            writer.writerow(['Tipo', 'Dados'])
                        for key, values in data.items():
                            writer.writerow([key, json.dumps(values, default=str)])
                    else:
                        writer = csv.DictWriter(f, fieldnames=data[0].keys() if data else [])
                        if include_headers:
                            writer.writeheader()
                        writer.writerows(data)
            elif format_type == 'xlsx':
                import pandas as pd
                filepath = f"exports/{filename}.xlsx"
                if export_type == 'all':
                    with pd.ExcelWriter(filepath) as writer:
                        for key, values in data.items():
                            df = pd.DataFrame(values)
                            df.to_excel(writer, sheet_name=key, index=False)
                else:
                    df = pd.DataFrame(data)
                    df.to_excel(filepath, index=False)
            
            # Comprime se solicitado
            if compress:
                import zipfile
                zip_path = f"{filepath}.zip"
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    zipf.write(filepath, os.path.basename(filepath))
                os.remove(filepath)  # Remove arquivo original
                filepath = zip_path
            
            # Atualiza registro de exportação
            export.file_path = filepath
            export.status = 'completed'
            export.save()
            
            # Retorna URL para download
            return JsonResponse({
                'status': 'completed',
                'message': 'Exportação concluída com sucesso',
                'download_url': reverse('admin_download', args=[export.id])
            })
            
        except Exception as e:
            export.status = 'failed'
            export.error_message = str(e)
            export.save()
            return JsonResponse({'error': str(e)}, status=500)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@user_passes_test(is_admin)
def download_export(request, export_id):
    """Download de arquivo exportado."""
    try:
        export = DataExport.objects.get(id=export_id, user=request.user)
        
        if export.status != 'completed':
            messages.error(request, 'Exportação ainda não concluída')
            return redirect('admin_export')
        
        if not os.path.exists(export.file_path):
            messages.error(request, 'Arquivo não encontrado')
            return redirect('admin_export')
        
        # Registra download
        export.download_count += 1
        export.last_download = timezone.now()
        export.save()
        
        # Retorna arquivo
        response = FileResponse(open(export.file_path, 'rb'))
        response['Content-Type'] = 'application/octet-stream'
        response['Content-Disposition'] = f'attachment; filename="{os.path.basename(export.file_path)}"'
        return response
        
    except DataExport.DoesNotExist:
        messages.error(request, 'Exportação não encontrada')
        return redirect('admin_export')
    except Exception as e:
        messages.error(request, f'Erro ao baixar arquivo: {str(e)}')
        return redirect('admin_export')

def terms_of_service(request):
    return render(request, 'hoztech/terms.html')

@require_http_methods(["POST"])
def download_pdf(request):
    """View otimizada para download de PDF com cache e validação"""
    try:
        # Extrai dados do POST
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        company = data.get('company', '').strip()
        role = data.get('role', '').strip()
        phone = data.get('phone', '').strip()
        marketing_consent = data.get('marketing_consent', False)

        # Valida campos obrigatórios
        if not name or not email:
            return JsonResponse({'error': 'Nome e e-mail são obrigatórios.'}, status=400)

        # Valida formato do e-mail
        try:
            validate_email(email)
        except ValidationError:
            return JsonResponse({'error': 'E-mail inválido.'}, status=400)

        # Gera chave de cache única
        cache_key = f"pdf_download_{email}_{int(time.time())}"
        
        # Verifica se já existe um download recente (evita spam)
        recent_downloads = cache.get(f"recent_downloads_{email}", [])
        if recent_downloads and (time.time() - recent_downloads[-1]) < 3600:  # 1 hora
            return JsonResponse({'error': 'Você já baixou o manual recentemente. Tente novamente mais tarde.'}, status=429)

        # Registra o download (assíncrono)
        try:
            DownloadRecord.objects.create(
                name=name,
                email=email,
                company=company,
                role=role,
                phone=phone,
                marketing_consent=marketing_consent,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )
        except Exception as e:
            logger.error(f"Erro ao registrar download: {str(e)}")
            # Não falha a requisição se o registro falhar

        # Atualiza cache de downloads recentes
        recent_downloads.append(time.time())
        cache.set(f"recent_downloads_{email}", recent_downloads[-5:], timeout=86400)  # Mantém últimos 5 downloads por 24h

        # Retorna URL do PDF (com cache)
        pdf_url = cache.get(cache_key)
        if not pdf_url:
            pdf_url = settings.MANUAL_PDF_URL  # URL do PDF em settings
            cache.set(cache_key, pdf_url, timeout=3600)  # Cache por 1 hora

        return JsonResponse({
            'success': True,
            'pdf_url': pdf_url,
            'message': 'Manual enviado com sucesso!'
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Dados inválidos.'}, status=400)
    except Exception as e:
        logger.error(f"Erro ao processar download: {str(e)}")
        return JsonResponse({'error': 'Erro ao processar sua solicitação.'}, status=500)

@login_required
@never_cache
def admin_downloads_list(request):
    """View para listar downloads realizados no painel customizado"""
    page = request.GET.get('page', 1)
    search = request.GET.get('search', '')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    user_filter = request.GET.get('user')
    marketing_filter = request.GET.get('marketing_consent')
    
    downloads = PDFDownload.objects.all()
    
    # Aplica filtros
    if search:
        downloads = downloads.filter(
            Q(name__icontains=search) |
            Q(email__icontains=search) |
            Q(company__icontains=search) |
            Q(role__icontains=search) |
            Q(phone__icontains=search) |
            Q(user__username__icontains=search)
        )
    
    if date_from:
        downloads = downloads.filter(created_at__gte=date_from)
    if date_to:
        downloads = downloads.filter(created_at__lte=date_to)
    if user_filter:
        downloads = downloads.filter(user__username=user_filter)
    if marketing_filter is not None:
        downloads = downloads.filter(marketing_consent=marketing_filter == 'true')
    
    # Ordenação
    sort_by = request.GET.get('sort', '-created_at')
    downloads = downloads.order_by(sort_by)
    
    # Paginação
    paginator = Paginator(downloads, 50)
    downloads_page = paginator.get_page(page)
    
    # Estatísticas
    total_downloads = downloads.count()
    total_users = downloads.values('user').distinct().count()
    total_companies = downloads.values('company').distinct().count()
    marketing_consents = downloads.filter(marketing_consent=True).count()
    
    # Últimos downloads
    recent_downloads = downloads.order_by('-created_at')[:5]
    
    # Downloads por usuário
    downloads_by_user = downloads.values('user__username').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    context = {
        'downloads': downloads_page,
        'search': search,
        'date_from': date_from,
        'date_to': date_to,
        'user_filter': user_filter,
        'marketing_filter': marketing_filter,
        'sort_by': sort_by,
        'total_downloads': total_downloads,
        'total_users': total_users,
        'total_companies': total_companies,
        'marketing_consents': marketing_consents,
        'recent_downloads': recent_downloads,
        'downloads_by_user': downloads_by_user,
        'users': User.objects.filter(pdf_downloads__isnull=False).distinct(),
    }
    
    return render(request, 'hoztech/admin/downloads_list.html', context)

@require_http_methods(["POST"])
@user_passes_test(lambda u: u.is_superuser)
def manage_cookies_api(request):
    """Endpoint seguro para gerenciar cookies via API"""
    try:
        data = json.loads(request.body)
        action = data.get('action')
        
        if not action or action not in ['list', 'export', 'cleanup', 'stats']:
            return JsonResponse({
                'status': 'error',
                'message': 'Ação inválida'
            }, status=400)
            
        # Captura a saída do comando
        output = io.StringIO()
        with redirect_stdout(output):
            # Executa o comando
            call_command(
                'manage_cookies',
                action=action,
                days=data.get('days', 30),
                output=data.get('output'),
                category=data.get('category', 'all')
            )
            
        # Obtém a saída
        command_output = output.getvalue()
        
        # Se for export, retorna o arquivo
        if action == 'export':
            output_file = data.get('output') or f'cookie_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.json'
            try:
                with open(output_file, 'r') as f:
                    export_data = json.load(f)
                return JsonResponse({
                    'status': 'success',
                    'message': command_output,
                    'data': export_data
                })
            except Exception as e:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Erro ao ler arquivo de exportação: {str(e)}'
                }, status=500)
        
        # Para outras ações, retorna a saída
        return JsonResponse({
            'status': 'success',
            'message': command_output
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Dados inválidos'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
def minha_seguranca(request):
    """
    View para exibir informações de segurança do cliente
    """
    try:
        # Obtém todas as informações do cliente
        ip, location_data, browser_info, connection_info = IPClientService.get_client_info(request)
        
        context = {
            'ip': ip,
            'location_data': location_data,
            'browser_info': browser_info,
            'connection_info': connection_info
        }
        
        return render(request, 'hoztech/minha_seguranca.html', context)
        
    except Exception as e:
        logger.error(f"Erro ao processar informações de segurança: {str(e)}")
        messages.error(request, "Ocorreu um erro ao processar suas informações de segurança.")
        return redirect('home')

def services(request):
    """
    View para a página de serviços.
    Retorna um template com a lista de serviços disponíveis.
    """
    services_list = [
        {
            'id': 'landing-page',
            'title': 'Landing Page Simples',
            'description': 'Página única responsiva com apresentação da empresa, link direto para WhatsApp e redes sociais, formulário de contato simples.',
            'icon': 'fa-solid fa-mobile-screen-button',
            'price': 199.00,
            'features': [
                'Design responsivo',
                'Formulário de contato',
                'Links para redes sociais',
                'Integração com WhatsApp',
                'Otimização para SEO básico'
            ]
        },
        {
            'id': 'site-institucional',
            'title': 'Site Institucional',
            'description': 'Até 6 páginas (Home, Sobre, Serviços, Portfólio, Blog e Contato) com design profissional, integração de newsletter e Google Analytics.',
            'icon': 'fa-solid fa-building',
            'price': 349.00,
            'features': [
                'Até 6 páginas',
                'Design profissional',
                'Newsletter integrada',
                'Google Analytics',
                'Blog integrado',
                'SEO otimizado'
            ]
        },
        {
            'id': 'loja-virtual',
            'title': 'Loja Virtual Básica',
            'description': 'E-commerce com até 50 produtos, carrinho de compras, integração com Pix, cartão de crédito e cálculo de frete automático.',
            'icon': 'fa-solid fa-cart-shopping',
            'price': 499.00,
            'features': [
                'Até 50 produtos',
                'Carrinho de compras',
                'Pagamento via Pix',
                'Cartão de crédito',
                'Cálculo de frete',
                'Painel administrativo'
            ]
        },
        {
            'id': 'suporte-premium',
            'title': 'Suporte Premium',
            'description': 'Tudo da Loja Virtual, mais manutenção contínua (atualizações ilimitadas de conteúdo), suporte 24/7 via chat e e-mail, relatório mensal de desempenho e otimizações SEO básicas.',
            'icon': 'fa-solid fa-headset',
            'price': 799.00,
            'features': [
                'Todas as features da Loja Virtual',
                'Manutenção contínua',
                'Suporte 24/7',
                'Relatórios mensais',
                'Otimizações SEO',
                'Atualizações ilimitadas'
            ]
        }
    ]
    
    return render(request, 'hoztech/services.html', {
        'services': services_list,
        'title': 'Nossos Serviços - Hoz Tech'
    })

@csrf_exempt
@require_http_methods(["POST"])
def service_request(request):
    """
    API endpoint para processar solicitações de serviços.
    Recebe dados via AJAX e retorna uma resposta JSON.
    """
    try:
        data = json.loads(request.body)
        nome = data.get('nome', '').strip()
        email = data.get('email', '').strip()
        telefone = data.get('telefone', '').strip()
        servico_id = data.get('servico_id')
        mensagem = data.get('mensagem', '').strip()

        # Validação básica
        if not all([nome, email, telefone, servico_id]):
            return JsonResponse({
                'success': False,
                'message': 'Por favor, preencha todos os campos obrigatórios.'
            })

        # Aqui você pode adicionar o código para salvar no banco de dados
        # ou enviar e-mail de notificação

        return JsonResponse({
            'success': True,
            'message': 'Solicitação recebida! Entraremos em contato em breve.'
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Erro ao processar os dados. Tente novamente.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Ocorreu um erro. Por favor, tente novamente mais tarde.'
        })

def sobre_nos(request):
    """
    View para a página sobre-nos.
    Retorna um template com informações sobre a empresa.
    """
    return render(request, 'hoztech/sobre_nos.html', {
        'title': 'Sobre Nós - Hoz Tech'
    })

def redirect_to_store(request):
    """Redirect to the store subdomain."""
    return redirect('https://loja.hoztech.com')

# Create your views here.
