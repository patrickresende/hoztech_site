from django.utils import timezone
from .models import VisitorAccess, CookieConsent
from user_agents import parse
from .ip_client import IPClientService
import uuid
import json
import logging
from django.db import DatabaseError
from django.core.cache import cache

logger = logging.getLogger(__name__)

class VisitorTrackingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.cache_timeout = 3600  # 1 hora

    def __call__(self, request):
        try:
            # Ignora requisições para arquivos estáticos e admin
            if not self._should_track(request):
                return self.get_response(request)

            # Captura informações do visitante
            ip_address = self._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            endpoint = request.path
            method = request.method

            logger.info(f"Rastreando visitante: IP={ip_address}, Endpoint={endpoint}, Method={method}")

            # Parse user agent
            try:
                ua = parse(user_agent)
                logger.info(f"User Agent parseado: Browser={ua.browser.family}, OS={ua.os.family}, Device={ua.device.family}")
            except Exception as e:
                logger.error(f"Erro ao parsear User Agent: {str(e)}")
                ua = None
            
            # Obtém localização do IP (com cache)
            location_data = self._get_ip_location(ip_address)
            logger.info(f"Localização obtida: {location_data}")
            
            # Cria ou atualiza o registro do visitante
            try:
                visitor = VisitorAccess.objects.create(
                    ip_address=ip_address,
                    user_agent=user_agent,
                    endpoint=endpoint,
                    method=method,
                    browser=ua.browser.family if ua else None,
                    os=ua.os.family if ua else None,
                    device_type=ua.device.family if ua else None,
                    session_id=request.session.session_key or str(uuid.uuid4()),
                    country=location_data.get('country'),
                    city=location_data.get('city'),
                    isp=location_data.get('isp')
                )
                logger.info(f"Visitante registrado com sucesso: {visitor.id}")
                
                # Captura cookies se houver consentimento
                self._process_cookies(request, visitor)
                
            except DatabaseError as e:
                logger.error(f"Erro ao salvar visitante: {str(e)}")
                # Continua a requisição mesmo com erro
                
        except Exception as e:
            logger.error(f"Erro no middleware de rastreamento: {str(e)}")
            # Continua a requisição mesmo com erro
            
        response = self.get_response(request)
        return response

    def _get_ip_location(self, ip_address):
        """Obtém a localização do IP com cache"""
        cache_key = f'ip_location_{ip_address}'
        location_data = cache.get(cache_key)
        
        if location_data is None:
            try:
                location_data = IPClientService.get_client_location(ip_address)
                cache.set(cache_key, location_data, self.cache_timeout)
            except Exception as e:
                logger.error(f"Erro ao obter localização do IP {ip_address}: {str(e)}")
                location_data = {}
                
        return location_data

    def _process_cookies(self, request, visitor):
        """Processa os cookies do visitante"""
        if 'cookie_consent' not in request.COOKIES:
            return
            
        try:
            consent_data = json.loads(request.COOKIES['cookie_consent'])
            for cookie_name, cookie_data in consent_data.items():
                if cookie_data.get('consent'):
                    try:
                        CookieConsent.objects.create(
                            visitor=visitor,
                            cookie_name=cookie_name[:100],  # Limita tamanho
                            value=cookie_data.get('value', '')[:1000],  # Limita tamanho
                            category=cookie_data.get('category', 'essential'),
                            expires_at=timezone.now() + timezone.timedelta(days=365)
                        )
                    except DatabaseError as e:
                        logger.error(f"Erro ao salvar cookie {cookie_name}: {str(e)}")
                        
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Erro ao processar cookies: {str(e)}")

    def _should_track(self, request):
        """Determina se a requisição deve ser rastreada"""
        # Ignora arquivos estáticos e mídia
        if request.path.startswith(('/static/', '/media/', '/admin/static/', '/admin/media/')):
            return False
        
        # Ignora requisições do admin Django
        if request.path.startswith('/admin/'):
            return False
            
        # Ignora requisições AJAX para atualização de cookies
        if request.path == '/api/cookies/preferences/' and request.method == 'POST':
            return False
            
        # Ignora bots conhecidos
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        bot_keywords = ['bot', 'crawler', 'spider', 'slurp', 'search', 'mediapartners', 'googlebot', 'bingbot', 'yandexbot']
        
        # Verifica se é um bot conhecido
        if any(keyword in user_agent for keyword in bot_keywords):
            logger.info(f"Ignorando bot: {user_agent}")
            return False
            
        # Verifica se tem user agent
        if not user_agent:
            logger.warning("Requisição sem User-Agent")
            return False
            
        # Verifica se tem IP
        if not self._get_client_ip(request):
            logger.warning("Requisição sem IP")
            return False
            
        return True

    def _get_client_ip(self, request):
        """Obtém o IP real do cliente"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip 