from django.utils import timezone
from .models import VisitorAccess, CookieConsent
from user_agents import parse
from .ip_client import IPClientService
import uuid
import json
import logging
from django.db import DatabaseError
from django.core.cache import cache
from django.conf import settings
from functools import lru_cache
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages

logger = logging.getLogger(__name__)

class VisitorTrackingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.cache_timeout = 3600  # 1 hora
        self.ip_client = IPClientService()
        self._bot_keywords = frozenset([
            'bot', 'crawler', 'spider', 'slurp', 'search', 
            'mediapartners', 'googlebot', 'bingbot', 'yandexbot'
        ])
        self._ignored_paths = frozenset([
            '/static/', '/media/', '/admin/static/', '/admin/media/',
            '/admin/', '/api/cookies/preferences/'
        ])

    def __call__(self, request):
        try:
            if not self._should_track(request):
                return self.get_response(request)

            # Captura informações do visitante
            ip_address = self._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            endpoint = request.path
            method = request.method
            referrer = request.META.get('HTTP_REFERER', '')
            language = request.META.get('HTTP_ACCEPT_LANGUAGE', '').split(',')[0] if request.META.get('HTTP_ACCEPT_LANGUAGE') else None
            screen_info = request.GET.get('screen_info')
            time_on_page = request.GET.get('time_on_page')

            # Cache key para evitar processamento duplicado
            cache_key = f'visitor_track:{ip_address}:{endpoint}:{method}'
            if cache.get(cache_key):
                return self.get_response(request)

            # Parse user agent (com cache)
            ua = self._parse_user_agent(user_agent)
            if not ua:
                return self.get_response(request)

            # Obtém localização do IP (com cache)
            location_data = self._get_ip_location(ip_address)
            
            # Processa informações da tela
            screen_data = {}
            if screen_info:
                try:
                    screen_data = json.loads(screen_info)
                except json.JSONDecodeError:
                    pass

            # Processa tempo na página
            try:
                time_on_page = int(time_on_page) if time_on_page else None
            except (ValueError, TypeError):
                time_on_page = None

            # Determina tipo de dispositivo
            is_mobile = ua.is_mobile
            is_tablet = ua.is_tablet
            is_desktop = ua.is_pc
            is_bot = ua.is_bot

            # Determina se é uma conversão
            is_conversion = self._is_conversion(request)
            conversion_type = self._get_conversion_type(request) if is_conversion else None

            # Obtém páginas visitadas da sessão
            session = request.session
            pages_visited = session.get('pages_visited', [])
            if endpoint not in pages_visited:
                pages_visited.append(endpoint)
                session['pages_visited'] = pages_visited[-10:]  # Mantém últimas 10 páginas

            # Determina se é um bounce
            is_bounce = len(pages_visited) <= 1 and time_on_page and time_on_page < 10

            # Cria o registro de acesso
            visitor_data = {
                'ip_address': ip_address,
                'user_agent': user_agent,
                'endpoint': endpoint,
                'method': method,
                'country': location_data.get('country'),
                'city': location_data.get('city'),
                'isp': location_data.get('isp'),
                'browser': ua.browser.family,
                'browser_version': ua.browser.version_string,
                'os': ua.os.family,
                'os_version': ua.os.version_string,
                'device_type': ua.device.family,
                'device_model': ua.device.model,
                'device_brand': ua.device.brand,
                'screen_width': screen_data.get('width'),
                'screen_height': screen_data.get('height'),
                'screen_resolution': f"{screen_data.get('width')}x{screen_data.get('height')}" if screen_data.get('width') and screen_data.get('height') else None,
                'referrer': referrer,
                'referrer_domain': self._get_domain_from_url(referrer) if referrer else None,
                'session_id': session.session_key or str(uuid.uuid4()),
                'time_on_page': time_on_page,
                'pages_visited': pages_visited,
                'is_bounce': is_bounce,
                'is_conversion': is_conversion,
                'conversion_type': conversion_type,
                'language': language,
                'timezone': location_data.get('timezone'),
                'is_mobile': is_mobile,
                'is_tablet': is_tablet,
                'is_desktop': is_desktop,
                'is_bot': is_bot,
            }
            
            # Armazena no cache para processamento em lote
            cache_key = f'visitor_batch:{timezone.now().strftime("%Y%m%d%H")}'
            batch = cache.get(cache_key, [])
            batch.append(visitor_data)
            cache.set(cache_key, batch, timeout=3600)  # 1 hora
            
            # Se o lote atingir o tamanho máximo, processa
            if len(batch) >= 100:  # Processa em lotes de 100
                self._process_visitor_batch(batch)
                cache.delete(cache_key)

            response = self.get_response(request)
            
            # Atualiza o tempo na página se disponível
            if time_on_page and hasattr(response, 'content'):
                try:
                    content = response.content.decode('utf-8')
                    if 'time_on_page' in content:
                        # Atualiza o tempo na página via JavaScript
                        script = f"""
                        <script>
                            window.addEventListener('beforeunload', function() {{
                                var timeSpent = Math.round((Date.now() - performance.now()) / 1000);
                                navigator.sendBeacon('{request.path}?time_on_page=' + timeSpent);
                            }});
                        </script>
                        """
                        response.content = content.replace('</body>', f'{script}</body>').encode('utf-8')
                except:
                    pass

            return response

        except Exception as e:
            logger.error(f"Erro no middleware de rastreamento: {str(e)}", exc_info=True)
            return self.get_response(request)

    @lru_cache(maxsize=1000)
    def _should_track(self, request):
        """Determina se a requisição deve ser rastreada (com cache)"""
        path = request.path
        
        # Verifica paths ignorados
        if any(path.startswith(ignored) for ignored in self._ignored_paths):
            return False
            
        # Verifica método HTTP
        if request.method not in ('GET', 'POST'):
            return False
            
        # Verifica user agent
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        if not user_agent or any(keyword in user_agent for keyword in self._bot_keywords):
            return False
            
        # Verifica IP
        if not self._get_client_ip(request):
            return False
            
        return True

    @lru_cache(maxsize=1000)
    def _get_client_ip(self, request):
        """Obtém o IP real do cliente (com cache)"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    @lru_cache(maxsize=1000)
    def _parse_user_agent(self, user_agent):
        """Parse user agent com cache"""
        try:
            return parse(user_agent)
        except Exception as e:
            logger.error(f"Erro ao parsear User Agent: {str(e)}")
            return None

    def _get_ip_location(self, ip_address):
        """Obtém localização do IP com cache"""
        cache_key = f'ip_location:{ip_address}'
        location_data = cache.get(cache_key)
        
        if location_data is None:
            try:
                location_data = self.ip_client.get_location(ip_address)
                if location_data:
                    cache.set(cache_key, location_data, timeout=self.cache_timeout)
            except Exception as e:
                logger.error(f"Erro ao obter localização do IP {ip_address}: {str(e)}")
                location_data = {}
        
        return location_data or {}

    def _process_visitor_batch(self, batch):
        """Processa um lote de registros de visitantes"""
        try:
            # Cria os registros em lote
            VisitorAccess.objects.bulk_create([
                VisitorAccess(**data) for data in batch
            ], batch_size=50)
        except DatabaseError as e:
            logger.error(f"Erro ao processar lote de visitantes: {str(e)}", exc_info=True)
        except Exception as e:
            logger.error(f"Erro inesperado ao processar lote: {str(e)}", exc_info=True)

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

    def _get_domain_from_url(self, url):
        """Extrai o domínio de uma URL"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc
        except:
            return None

    def _is_conversion(self, request):
        """Determina se a requisição é uma conversão"""
        conversion_paths = {
            '/contato/': 'contact',
            '/download-pdf/': 'download',
            '/service-request/': 'service',
            '/checkout/': 'purchase'
        }
        return request.path in conversion_paths

    def _get_conversion_type(self, request):
        """Obtém o tipo de conversão"""
        conversion_paths = {
            '/contato/': 'contact',
            '/download-pdf/': 'download',
            '/service-request/': 'service',
            '/checkout/': 'purchase'
        }
        return conversion_paths.get(request.path)

class AdminSessionTimeoutMiddleware:
    """Middleware para gerenciar o timeout da sessão administrativa"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.user.is_authenticated and hasattr(request.user, 'auth_preference'):
            # Verifica se é uma rota administrativa
            if request.path.startswith('/admin-auth-user/'):
                # Obtém o timeout configurado (em minutos)
                timeout_minutes = request.user.auth_preference.session_timeout
                
                # Verifica se a sessão expirou
                last_activity = request.session.get('last_activity')
                if last_activity:
                    last_activity = timezone.datetime.fromisoformat(last_activity)
                    if (timezone.now() - last_activity).total_seconds() > timeout_minutes * 60:
                        # Sessão expirada
                        logout(request)
                        messages.warning(request, 'Sua sessão expirou por inatividade.')
                        return redirect('admin_login')
                
                # Atualiza o timestamp da última atividade
                request.session['last_activity'] = timezone.now().isoformat()
        
        response = self.get_response(request)
        return response

class AdminIPRestrictionMiddleware:
    """Middleware para restringir acesso por IP"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.user.is_authenticated and hasattr(request.user, 'auth_preference'):
            # Verifica se é uma rota administrativa
            if request.path.startswith('/admin-auth-user/'):
                client_ip = self._get_client_ip(request)
                auth_pref = request.user.auth_preference
                
                # Se houver IPs permitidos configurados
                if auth_pref.allowed_ips and not auth_pref.is_ip_allowed(client_ip):
                    logout(request)
                    messages.error(request, 'Acesso não permitido deste IP.')
                    return redirect('admin_login')
        
        response = self.get_response(request)
        return response
    
    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip 