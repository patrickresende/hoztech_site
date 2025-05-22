from django.db import models
from django.utils import timezone
import uuid

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
    
    # Informações adicionais
    browser = models.CharField(max_length=100, blank=True, null=True)
    os = models.CharField(max_length=100, blank=True, null=True)
    device_type = models.CharField(max_length=50, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    
    # Histórico de mudanças
    change_history = models.JSONField(default=list, blank=True)
    
    class Meta:
        verbose_name = 'Preferência de Cookie'
        verbose_name_plural = 'Preferências de Cookies'
        ordering = ['-last_visit']
    
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
        
        # Registra a mudança no histórico
        change_entry = {
            'timestamp': timezone.now().isoformat(),
            'old_preferences': old_preferences,
            'new_preferences': preferences,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent
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
        """Atualiza informações do navegador usando o user_agent"""
        if not self.user_agent:
            return
            
        # Aqui você pode usar uma biblioteca como user-agents para parsear o user_agent
        # Por exemplo: https://github.com/selwin/python-user-agents
        try:
            from user_agents import parse
            ua = parse(self.user_agent)
            
            self.browser = f"{ua.browser.family} {ua.browser.version_string}"
            self.os = f"{ua.os.family} {ua.os.version_string}"
            self.device_type = ua.device.family
            
            if ua.is_mobile:
                self.device_type = 'Mobile'
            elif ua.is_tablet:
                self.device_type = 'Tablet'
            elif ua.is_pc:
                self.device_type = 'Desktop'
            elif ua.is_bot:
                self.device_type = 'Bot'
        except:
            # Se houver erro no parse, mantém os valores atuais
            pass
