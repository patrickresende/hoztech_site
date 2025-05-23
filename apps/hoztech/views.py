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
from django.contrib.auth.decorators import login_required
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
    # Obtém informações do cliente usando o novo serviço
    client_ip, location_data = IPClientService.get_client_info(request)
    location_string = IPClientService.format_location_string(location_data)
    
    context = {
        'client_ip': client_ip,
        'client_location': location_string,
        'location_data': location_data  # Dados completos para uso futuro
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

class AdminLoginView(LoginView):
    template_name = 'hoztech/admin/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        return reverse_lazy('admin_dashboard')
    
    def form_valid(self, form):
        user = form.get_user()
        login(self.request, user)
        AdminAccessLog.objects.create(
            user=user,
            ip_address=get_client_ip(self.request),
            action='login_attempt',
            success=True
        )
        return redirect('admin_dashboard')
    
    def form_invalid(self, form):
        # Registra a tentativa de login falha
        AdminAccessLog.objects.create(
            ip_address=get_client_ip(self.request),
            action='login_failed',
            details={'username': form.cleaned_data.get('username')},
            success=False
        )
        return super().form_invalid(form)

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
        
        # Estatísticas gerais
        now = timezone.now()
        last_30_days = now - timedelta(days=30)
        
        context.update({
            'total_visitors': VisitorAccess.objects.count(),
            'total_cookies': CookieConsent.objects.count(),
            'visitors_30d': VisitorAccess.objects.filter(timestamp__gte=last_30_days).count(),
            'unique_ips_30d': VisitorAccess.objects.filter(timestamp__gte=last_30_days).values('ip_address').distinct().count(),
            'top_countries': VisitorAccess.objects.exclude(country__isnull=True).values('country').annotate(count=Count('id')).order_by('-count')[:5],
            'top_browsers': VisitorAccess.objects.exclude(browser__isnull=True).values('browser').annotate(count=Count('id')).order_by('-count')[:5],
            'recent_visitors': VisitorAccess.objects.select_related().order_by('-timestamp')[:10],
            'recent_exports': DataExport.objects.filter(user=self.request.user).order_by('-timestamp')[:5],
        })
        
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
    search = request.GET.get('search', '')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    visitors = VisitorAccess.objects.all()
    
    if search:
        visitors = visitors.filter(
            Q(ip_address__icontains=search) |
            Q(country__icontains=search) |
            Q(city__icontains=search) |
            Q(browser__icontains=search)
        )
    
    if date_from:
        visitors = visitors.filter(timestamp__gte=date_from)
    if date_to:
        visitors = visitors.filter(timestamp__lte=date_to)
    
    paginator = Paginator(visitors, 50)
    visitors_page = paginator.get_page(page)
    
    return render(request, 'hoztech/admin/visitor_list.html', {
        'visitors': visitors_page,
        'search': search,
        'date_from': date_from,
        'date_to': date_to
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
    
    return render(request, 'hoztech/admin/cookie_list.html', {
        'cookies': cookies_page,
        'search': search,
        'category': category,
        'date_from': date_from,
        'date_to': date_to,
        'categories': CookieConsent._meta.get_field('category').choices
    })

@method_decorator(never_cache, name='dispatch')
class AdminExportView(LoginRequiredMixin, TemplateView):
    template_name = 'hoztech/admin/export.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Adiciona dados de contexto se necessário
        return context

@login_required
@require_http_methods(['POST'])
@csrf_protect
def export_data(request):
    try:
        export_type = request.POST.get('export_type')
        date_from = request.POST.get('date_from')
        date_to = request.POST.get('date_to')
        format_type = request.POST.get('format', 'json')
        
        if not all([export_type, date_from, date_to]):
            messages.error(request, 'Parâmetros inválidos')
            return redirect('admin_export')
        
        # Obtém os dados
        if export_type == 'cookies':
            data = CookieConsent.objects.filter(
                timestamp__range=[date_from, date_to]
            ).select_related('visitor')
        elif export_type == 'access':
            data = VisitorAccess.objects.filter(
                timestamp__range=[date_from, date_to]
            )
        else:  # all
            data = {
                'cookies': CookieConsent.objects.filter(
                    timestamp__range=[date_from, date_to]
                ).select_related('visitor'),
                'access': VisitorAccess.objects.filter(
                    timestamp__range=[date_from, date_to]
                )
            }
        
        # Gera o nome do arquivo
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"export_{export_type}_{timestamp}.{format_type}"
        
        # Prepara os dados para exportação
        if format_type == 'json':
            if export_type == 'all':
                export_data = {
                    'cookies': list(data['cookies'].values()),
                    'access': list(data['access'].values())
                }
            else:
                export_data = list(data.values())
            
            response = HttpResponse(
                json.dumps(export_data, default=str, indent=2, ensure_ascii=False),
                content_type='application/json'
            )
        else:  # csv
            response = HttpResponse(
                content_type='text/csv',
                headers={'Content-Disposition': f'attachment; filename="{filename}"'}
            )
            
            writer = csv.writer(response)
            if export_type == 'all':
                # Escreve cookies
                writer.writerow(['Cookie Data'])
                writer.writerow(['ID', 'Cookie Name', 'Value', 'Category', 'Timestamp', 'IP Address'])
                for cookie in data['cookies']:
                    writer.writerow([
                        cookie.id, cookie.cookie_name, cookie.value,
                        cookie.category, cookie.timestamp, cookie.visitor.ip_address
                    ])
                writer.writerow([])
                # Escreve acessos
                writer.writerow(['Access Data'])
                writer.writerow(['ID', 'IP Address', 'Browser', 'OS', 'Timestamp', 'Country', 'City'])
                for access in data['access']:
                    writer.writerow([
                        access.id, access.ip_address, access.browser,
                        access.os, access.timestamp, access.country, access.city
                    ])
            else:
                if export_type == 'cookies':
                    writer.writerow(['ID', 'Cookie Name', 'Value', 'Category', 'Timestamp', 'IP Address'])
                    for cookie in data:
                        writer.writerow([
                            cookie.id, cookie.cookie_name, cookie.value,
                            cookie.category, cookie.timestamp, cookie.visitor.ip_address
                        ])
                else:  # access
                    writer.writerow(['ID', 'IP Address', 'Browser', 'OS', 'Timestamp', 'Country', 'City'])
                    for access in data:
                        writer.writerow([
                            access.id, access.ip_address, access.browser,
                            access.os, access.timestamp, access.country, access.city
                        ])
        
        # Configura o cabeçalho para download
        if format_type == 'json':
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Registra o acesso
        AdminAccessLog.objects.create(
            user=request.user,
            ip_address=get_client_ip(request),
            action=f'export_{export_type}',
            details={'format': format_type, 'date_range': f"{date_from} to {date_to}"},
            success=True
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Erro na exportação: {str(e)}")
        messages.error(request, f'Erro ao exportar dados: {str(e)}')
        return redirect('admin_export')

@login_required
@never_cache
def download_export(request, export_id):
    try:
        export = DataExport.objects.get(id=export_id, user=request.user)
        
        if export.status != 'completed':
            raise PermissionDenied("Exportação não está pronta")
        
        if not os.path.exists(export.file_path):
            raise FileNotFoundError("Arquivo não encontrado")
        
        # Registra o download
        AdminAccessLog.objects.create(
            user=request.user,
            ip_address=get_client_ip(request),
            action='download_export',
            details={'export_id': str(export_id)},
            success=True
        )
        
        return FileResponse(
            open(export.file_path, 'rb'),
            as_attachment=True,
            filename=os.path.basename(export.file_path)
        )
        
    except (DataExport.DoesNotExist, PermissionDenied, FileNotFoundError) as e:
        messages.error(request, str(e))
        return redirect('admin_dashboard')

def terms_of_service(request):
    return render(request, 'hoztech/terms.html')

@require_http_methods(['POST'])
def download_pdf(request):
    if request.method == 'POST':
        try:
            # Validação dos campos obrigatórios
            name = request.POST.get('name', '').strip()
            email = request.POST.get('email', '').strip()
            
            if not name or not email:
                return JsonResponse({
                    'success': False,
                    'message': 'Nome e e-mail são obrigatórios.'
                }, status=400)
            
            # Validação do formato do e-mail
            if not '@' in email or not '.' in email:
                return JsonResponse({
                    'success': False,
                    'message': 'Por favor, forneça um e-mail válido.'
                }, status=400)
            
            # Criação do registro de download
            pdf_download = PDFDownload.objects.create(
                name=name,
                email=email,
                company=request.POST.get('company', '').strip(),
                role=request.POST.get('role', '').strip(),
                phone=request.POST.get('phone', '').strip(),
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                marketing_consent=request.POST.get('marketing_consent') == 'true',
                source=request.POST.get('source', 'site'),
                user=request.user if request.user.is_authenticated else None
            )
            
            # Caminho do arquivo PDF
            pdf_path = os.path.join(settings.MEDIA_ROOT, 'O Manual da Cybersegurança - Vol 1.pdf')
            
            if not os.path.exists(pdf_path):
                logger.error(f'Arquivo PDF não encontrado em: {pdf_path}')
                return JsonResponse({
                    'success': False,
                    'message': 'Erro ao processar o download. Por favor, tente novamente.'
                }, status=500)
            
            # Incrementa o contador de downloads
            pdf_download.increment_download_count()
            
            # Retorna a URL do PDF para download
            return JsonResponse({
                'success': True,
                'pdf_url': request.build_absolute_uri('/media/O Manual da Cybersegurança - Vol 1.pdf')
            })
            
        except Exception as e:
            logger.error(f'Erro ao processar download: {str(e)}')
            return JsonResponse({
                'success': False,
                'message': 'Erro ao processar o download. Por favor, tente novamente.'
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'message': 'Método não permitido.'
    }, status=405)

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

# Create your views here.
