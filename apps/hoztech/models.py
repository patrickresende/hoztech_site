from django.db import models
from django.utils import timezone
import uuid
import json
from user_agents import parse

class CookiePreference(models.Model):
    # Identificador único para o cliente
    client_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # Informações do navegador
    user_agent = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    
    # Preferências de cookies
    essential_cookies = models.BooleanField(default=True)  # Sempre True
    performance_cookies = models.BooleanField(default=True)
    marketing_cookies = models.BooleanField(default=True)
    
    # Metadados
    first_visit = models.DateTimeField(default=timezone.now)
    last_visit = models.DateTimeField(auto_now=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    # Informações detalhadas do dispositivo
    browser = models.CharField(max_length=100, blank=True, null=True)
    browser_version = models.CharField(max_length=50, blank=True, null=True)
    os = models.CharField(max_length=100, blank=True, null=True)
    os_version = models.CharField(max_length=50, blank=True, null=True)
    device_type = models.CharField(max_length=50, blank=True, null=True)
    device_brand = models.CharField(max_length=100, blank=True, null=True)
    device_model = models.CharField(max_length=100, blank=True, null=True)
    is_mobile = models.BooleanField(default=False)
    is_tablet = models.BooleanField(default=False)
    is_pc = models.BooleanField(default=False)
    is_bot = models.BooleanField(default=False)
    is_touch_capable = models.BooleanField(default=False)
    
    # Informações de localização
    country = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    region = models.CharField(max_length=100, blank=True, null=True)
    timezone = models.CharField(max_length=50, blank=True, null=True)
    
    # Informações de tela
    screen_width = models.IntegerField(blank=True, null=True)
    screen_height = models.IntegerField(blank=True, null=True)
    screen_resolution = models.CharField(max_length=50, blank=True, null=True)
    
    # Histórico de mudanças
    change_history = models.JSONField(default=list, blank=True)
    
    class Meta:
        verbose_name = 'Preferência de Cookie'
        verbose_name_plural = 'Preferências de Cookies'
        ordering = ['-last_visit']
        indexes = [
            models.Index(fields=['device_type']),
            models.Index(fields=['browser']),
            models.Index(fields=['os']),
            models.Index(fields=['last_visit']),
            models.Index(fields=['is_mobile', 'is_tablet', 'is_pc']),
        ]
    
    def __str__(self):
        return f"Cookie Preferences - {self.client_id} ({self.last_visit.strftime('%Y-%m-%d %H:%M')})"
    
    def update_preferences(self, preferences, request=None):
        """Atualiza as preferências e registra a mudança no histórico"""
        old_preferences = {
            'essential': self.essential_cookies,
            'performance': self.performance_cookies,
            'marketing': self.marketing_cookies
        }
        
        # Atualiza as preferências
        self.performance_cookies = preferences.get('performance', True)
        self.marketing_cookies = preferences.get('marketing', True)
        
        # Atualiza informações do cliente se disponíveis
        if request:
            self.user_agent = request.META.get('HTTP_USER_AGENT', '')
            self.ip_address = self.get_client_ip(request)
            self.update_browser_info()
            
            # Atualiza informações de tela se disponíveis
            screen_info = request.GET.get('screen_info')
            if screen_info:
                try:
                    screen_data = json.loads(screen_info)
                    self.screen_width = screen_data.get('width')
                    self.screen_height = screen_data.get('height')
                    self.screen_resolution = f"{self.screen_width}x{self.screen_height}"
                except:
                    pass
        
        # Registra a mudança no histórico
        change_entry = {
            'timestamp': timezone.now().isoformat(),
            'old_preferences': old_preferences,
            'new_preferences': preferences,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'screen_info': {
                'width': self.screen_width,
                'height': self.screen_height,
                'resolution': self.screen_resolution
            } if self.screen_width and self.screen_height else None
        }
        
        if not isinstance(self.change_history, list):
            self.change_history = []
        
        self.change_history.append(change_entry)
        self.save()
    
    def get_client_ip(self, request):
        """Obtém o IP real do cliente"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def update_browser_info(self):
        """Atualiza informações detalhadas do navegador usando o user_agent"""
        if not self.user_agent:
            return
            
        try:
            ua = parse(self.user_agent)
            
            # Informações do navegador
            self.browser = ua.browser.family
            self.browser_version = ua.browser.version_string
            
            # Informações do sistema operacional
            self.os = ua.os.family
            self.os_version = ua.os.version_string
            
            # Informações do dispositivo
            self.device_type = ua.device.family
            self.device_brand = ua.device.brand
            self.device_model = ua.device.model
            
            # Flags de tipo de dispositivo
            self.is_mobile = ua.is_mobile
            self.is_tablet = ua.is_tablet
            self.is_pc = ua.is_pc
            self.is_bot = ua.is_bot
            self.is_touch_capable = ua.is_touch_capable
            
            # Define o tipo de dispositivo principal
            if ua.is_mobile:
                self.device_type = 'Mobile'
            elif ua.is_tablet:
                self.device_type = 'Tablet'
            elif ua.is_pc:
                self.device_type = 'Desktop'
            elif ua.is_bot:
                self.device_type = 'Bot'
                
        except Exception as e:
            print(f"Erro ao processar user agent: {str(e)}")
            # Mantém os valores atuais em caso de erro
