from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
import uuid
import json
from user_agents import parse
from django.db.models import Index, Count, Avg, Q, FloatField
from django.core.cache import cache
from django.conf import settings
from datetime import timedelta
from django.db.models.functions import Cast
import os

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

class VisitorAccess(models.Model):
    """Modelo para registrar acessos de visitantes"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ip_address = models.GenericIPAddressField(db_index=True)
    user_agent = models.TextField()
    endpoint = models.CharField(max_length=255, db_index=True)
    method = models.CharField(max_length=10)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    country = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    isp = models.CharField(max_length=255, null=True, blank=True)
    browser = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    browser_version = models.CharField(max_length=50, null=True, blank=True)
    os = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    os_version = models.CharField(max_length=50, null=True, blank=True)
    device_type = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    device_model = models.CharField(max_length=100, null=True, blank=True)
    device_brand = models.CharField(max_length=100, null=True, blank=True)
    screen_width = models.IntegerField(null=True, blank=True)
    screen_height = models.IntegerField(null=True, blank=True)
    screen_resolution = models.CharField(max_length=50, null=True, blank=True)
    referrer = models.URLField(max_length=500, null=True, blank=True)
    referrer_domain = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    session_id = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    time_on_page = models.IntegerField(null=True, blank=True, help_text="Tempo em segundos")
    pages_visited = models.JSONField(default=list, blank=True, help_text="Lista de páginas visitadas em sequência")
    is_bounce = models.BooleanField(default=False, help_text="Visitante saiu sem interagir")
    is_conversion = models.BooleanField(default=False, help_text="Visitante realizou uma conversão")
    conversion_type = models.CharField(max_length=50, null=True, blank=True, help_text="Tipo de conversão (download, contato, etc)")
    language = models.CharField(max_length=10, null=True, blank=True)
    timezone = models.CharField(max_length=50, null=True, blank=True)
    is_mobile = models.BooleanField(default=False, db_index=True)
    is_tablet = models.BooleanField(default=False, db_index=True)
    is_desktop = models.BooleanField(default=False, db_index=True)
    is_bot = models.BooleanField(default=False, db_index=True)
    
    class Meta:
        indexes = [
            Index(fields=['ip_address', 'timestamp']),
            Index(fields=['session_id', 'timestamp']),
            Index(fields=['browser', 'os', 'device_type']),
            Index(fields=['country', 'city']),
            Index(fields=['is_mobile', 'is_tablet', 'is_desktop']),
            Index(fields=['is_conversion', 'conversion_type']),
            Index(fields=['referrer_domain']),
        ]
        ordering = ['-timestamp']
        verbose_name = 'Acesso de Visitante'
        verbose_name_plural = 'Acessos de Visitantes'
        get_latest_by = 'timestamp'

    def __str__(self):
        return f"{self.ip_address} - {self.timestamp}"

    @property
    def screen_size(self):
        """Retorna a resolução da tela formatada"""
        if self.screen_width and self.screen_height:
            return f"{self.screen_width}x{self.screen_height}"
        return None

    @property
    def device_info(self):
        """Retorna informações do dispositivo formatadas"""
        parts = []
        if self.device_brand:
            parts.append(self.device_brand)
        if self.device_model:
            parts.append(self.device_model)
        if self.device_type:
            parts.append(self.device_type)
        return " ".join(parts) if parts else None

    @property
    def browser_info(self):
        """Retorna informações do navegador formatadas"""
        if self.browser and self.browser_version:
            return f"{self.browser} {self.browser_version}"
        return self.browser or None

    @property
    def os_info(self):
        """Retorna informações do sistema operacional formatadas"""
        if self.os and self.os_version:
            return f"{self.os} {self.os_version}"
        return self.os or None

    @classmethod
    def get_visitor_stats(cls, days=30):
        """Retorna estatísticas de visitantes para o período especificado"""
        start_date = timezone.now() - timedelta(days=days)
        
        # Filtra registros do período
        visitors = cls.objects.filter(timestamp__gte=start_date)
        
        # Estatísticas básicas
        total_visits = visitors.count()
        unique_visitors = visitors.values('ip_address').distinct().count()
        
        # Estatísticas por dispositivo
        device_stats = visitors.values('device_type').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        # Estatísticas por navegador
        browser_stats = visitors.values('browser').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        # Estatísticas por país
        country_stats = visitors.values('country').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        # Estatísticas de conversão
        conversion_stats = visitors.filter(is_conversion=True).values(
            'conversion_type'
        ).annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Estatísticas de bounce
        bounce_rate = visitors.filter(is_bounce=True).count() / total_visits * 100 if total_visits > 0 else 0
        
        # Tempo médio na página
        avg_time = visitors.exclude(time_on_page__isnull=True).aggregate(
            avg_time=Avg('time_on_page')
        )['avg_time'] or 0
        
        return {
            'total_visits': total_visits,
            'unique_visitors': unique_visitors,
            'device_stats': list(device_stats),
            'browser_stats': list(browser_stats),
            'country_stats': list(country_stats),
            'conversion_stats': list(conversion_stats),
            'bounce_rate': round(bounce_rate, 2),
            'avg_time_on_page': round(avg_time, 2),
            'period_days': days
        }

    @classmethod
    def cleanup_old_records(cls, days=90):
        """Remove registros antigos para manter o banco de dados otimizado"""
        cutoff_date = timezone.now() - timedelta(days=days)
        deleted, _ = cls.objects.filter(timestamp__lt=cutoff_date).delete()
        return deleted

class CookieConsent(models.Model):
    """Modelo para registrar consentimentos de cookies"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visitor = models.ForeignKey(VisitorAccess, on_delete=models.CASCADE, related_name='cookie_consents', db_index=True)
    cookie_name = models.CharField(max_length=100, db_index=True)
    value = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    category = models.CharField(max_length=50, choices=[
        ('essential', 'Essencial'),
        ('performance', 'Desempenho'),
        ('marketing', 'Marketing'),
        ('analytics', 'Analytics'),
        ('preferences', 'Preferências'),
        ('security', 'Segurança')
    ], db_index=True)
    browser_version = models.CharField(max_length=50, null=True, blank=True)
    browser_settings = models.JSONField(default=dict, blank=True, help_text="Configurações de privacidade do navegador")
    consent_source = models.CharField(max_length=50, choices=[
        ('banner', 'Banner de Cookies'),
        ('settings', 'Configurações'),
        ('preferences', 'Preferências do Usuário'),
        ('auto', 'Automático')
    ], default='banner')
    consent_method = models.CharField(max_length=50, choices=[
        ('click', 'Clique'),
        ('scroll', 'Scroll'),
        ('auto', 'Automático'),
        ('settings', 'Configurações')
    ], default='click')
    consent_duration = models.IntegerField(null=True, blank=True, help_text="Duração do consentimento em dias")
    is_third_party = models.BooleanField(default=False, help_text="Cookie de terceiros")
    third_party_domain = models.CharField(max_length=255, null=True, blank=True)
    purpose = models.TextField(null=True, blank=True, help_text="Propósito do cookie")
    data_retention = models.IntegerField(null=True, blank=True, help_text="Período de retenção em dias")
    
    class Meta:
        indexes = [
            Index(fields=['cookie_name', 'timestamp']),
            Index(fields=['category', 'timestamp']),
            Index(fields=['visitor', 'category']),
            Index(fields=['is_third_party', 'third_party_domain']),
            Index(fields=['consent_source', 'consent_method']),
        ]
        ordering = ['-timestamp']
        verbose_name = 'Consentimento de Cookie'
        verbose_name_plural = 'Consentimentos de Cookies'
        get_latest_by = 'timestamp'

    def __str__(self):
        return f"{self.cookie_name} - {self.timestamp}"

    @property
    def is_expired(self):
        """Verifica se o consentimento expirou"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at

    @property
    def days_until_expiry(self):
        """Retorna o número de dias até a expiração"""
        if not self.expires_at:
            return None
        delta = self.expires_at - timezone.now()
        return max(0, delta.days)

    @classmethod
    def get_consent_stats(cls, days=30):
        """Retorna estatísticas de consentimento para o período especificado"""
        start_date = timezone.now() - timedelta(days=days)
        
        # Filtra registros do período
        consents = cls.objects.filter(timestamp__gte=start_date)
        
        # Estatísticas básicas
        total_consents = consents.count()
        
        # Estatísticas por categoria
        category_stats = consents.values('category').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Estatísticas por cookie
        cookie_stats = consents.values('cookie_name').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        # Estatísticas por país
        country_stats = consents.values('visitor__country').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        # Estatísticas por navegador
        browser_stats = consents.values('visitor__browser').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        # Estatísticas de terceiros
        third_party_stats = consents.filter(is_third_party=True).values(
            'third_party_domain'
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        # Taxa de aceitação por categoria
        acceptance_rates = {}
        for category in dict(cls._meta.get_field('category').choices).keys():
            category_total = consents.filter(category=category).count()
            if total_consents > 0:
                rate = (category_total / total_consents) * 100
                acceptance_rates[category] = round(rate, 2)
            else:
                acceptance_rates[category] = 0
        
        return {
            'total_consents': total_consents,
            'category_stats': list(category_stats),
            'cookie_stats': list(cookie_stats),
            'country_stats': list(country_stats),
            'browser_stats': list(browser_stats),
            'third_party_stats': list(third_party_stats),
            'acceptance_rates': acceptance_rates,
            'period_days': days
        }

    @classmethod
    def cleanup_expired_consents(cls):
        """Remove consentimentos expirados"""
        expired = cls.objects.filter(expires_at__lt=timezone.now())
        count = expired.count()
        expired.delete()
        return count

class AdminAccessLog(models.Model):
    """Modelo para registrar acessos à área administrativa"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    ip_address = models.GenericIPAddressField()
    timestamp = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=100)
    details = models.JSONField(null=True, blank=True)
    success = models.BooleanField(default=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['action']),
        ]
        ordering = ['-timestamp']
        verbose_name = 'Log de Acesso Administrativo'
        verbose_name_plural = 'Logs de Acesso Administrativo'

    def __str__(self):
        return f"{self.user.username if self.user else 'Unknown'} - {self.action} - {self.timestamp}"

class AdminAuthImage(models.Model):
    """Modelo para armazenar imagens de autenticação 2FA"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    image = models.ImageField(upload_to='admin_auth_images/')
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['is_active']),
        ]
        ordering = ['category', 'name']
        verbose_name = 'Imagem de Autenticação'
        verbose_name_plural = 'Imagens de Autenticação'

    def __str__(self):
        return f"{self.name} ({self.category})"

class AdminUserAuthPreference(models.Model):
    """Modelo para armazenar preferências de autenticação dos usuários"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='auth_preference')
    auth_images = models.ManyToManyField(AdminAuthImage, related_name='selected_by_users')
    is_2fa_enabled = models.BooleanField(default=True)
    last_auth_image = models.ForeignKey(AdminAuthImage, on_delete=models.SET_NULL, null=True, blank=True, related_name='last_used_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Campos de segurança
    login_attempts = models.IntegerField(default=0)
    last_login_attempt = models.DateTimeField(null=True, blank=True)
    is_locked = models.BooleanField(default=False)
    lock_expires_at = models.DateTimeField(null=True, blank=True)
    require_password_change = models.BooleanField(default=False)
    last_password_change = models.DateTimeField(null=True, blank=True)
    session_timeout = models.IntegerField(default=30)  # minutos
    allowed_ips = models.JSONField(default=list, blank=True)
    notify_on_login = models.BooleanField(default=True)
    notify_on_password_change = models.BooleanField(default=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['is_2fa_enabled']),
            models.Index(fields=['is_locked']),
            models.Index(fields=['last_login_attempt']),
            models.Index(fields=['require_password_change']),
        ]
        verbose_name = 'Preferência de Autenticação'
        verbose_name_plural = 'Preferências de Autenticação'

    def __str__(self):
        return f"Preferências de {self.user.username}"

    def increment_login_attempts(self):
        """Incrementa o contador de tentativas de login"""
        self.login_attempts += 1
        self.last_login_attempt = timezone.now()
        
        # Bloqueia após 5 tentativas por 30 minutos
        if self.login_attempts >= 5:
            self.is_locked = True
            self.lock_expires_at = timezone.now() + timedelta(minutes=30)
        
        self.save()

    def reset_login_attempts(self):
        """Reseta o contador de tentativas de login"""
        self.login_attempts = 0
        self.is_locked = False
        self.lock_expires_at = None
        self.save()

    def check_lock_status(self):
        """Verifica se a conta está bloqueada"""
        if self.is_locked and self.lock_expires_at:
            if timezone.now() > self.lock_expires_at:
                self.reset_login_attempts()
                return False
            return True
        return False

    def add_allowed_ip(self, ip_address):
        """Adiciona um IP à lista de IPs permitidos"""
        if ip_address not in self.allowed_ips:
            self.allowed_ips.append(ip_address)
            self.save()

    def remove_allowed_ip(self, ip_address):
        """Remove um IP da lista de IPs permitidos"""
        if ip_address in self.allowed_ips:
            self.allowed_ips.remove(ip_address)
            self.save()

    def is_ip_allowed(self, ip_address):
        """Verifica se um IP está na lista de IPs permitidos"""
        return not self.allowed_ips or ip_address in self.allowed_ips

class DataExport(models.Model):
    """Modelo para registro de exportações de dados."""
    
    EXPORT_TYPES = [
        ('cookies', 'Cookies'),
        ('access', 'Acessos'),
        ('all', 'Todos os Dados')
    ]
    
    FORMAT_TYPES = [
        ('json', 'JSON'),
        ('csv', 'CSV'),
        ('xlsx', 'Excel (XLSX)')
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('processing', 'Processando'),
        ('completed', 'Concluído'),
        ('failed', 'Falhou')
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='exports',
        verbose_name='Usuário'
    )
    
    export_type = models.CharField(
        max_length=10,
        choices=EXPORT_TYPES,
        verbose_name='Tipo de Exportação'
    )
    
    date_range_start = models.DateField(
        verbose_name='Data Inicial'
    )
    
    date_range_end = models.DateField(
        verbose_name='Data Final'
    )
    
    format = models.CharField(
        max_length=10,
        choices=FORMAT_TYPES,
        default='json',
        verbose_name='Formato'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Status'
    )
    
    file_path = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='Caminho do Arquivo'
    )
    
    error_message = models.TextField(
        null=True,
        blank=True,
        verbose_name='Mensagem de Erro'
    )
    
    compress = models.BooleanField(
        default=False,
        verbose_name='Comprimido'
    )
    
    include_headers = models.BooleanField(
        default=True,
        verbose_name='Incluir Cabeçalhos'
    )
    
    download_count = models.PositiveIntegerField(
        default=0,
        verbose_name='Downloads'
    )
    
    last_download = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Último Download'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Criado em'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Atualizado em'
    )
    
    class Meta:
        verbose_name = 'Exportação'
        verbose_name_plural = 'Exportações'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'export_type', 'status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['status'])
        ]
    
    def __str__(self):
        return f"{self.get_export_type_display()} - {self.date_range_start} a {self.date_range_end}"
    
    def get_file_name(self):
        """Retorna o nome do arquivo para download."""
        if not self.file_path:
            return None
        return os.path.basename(self.file_path)
    
    def get_file_size(self):
        """Retorna o tamanho do arquivo em bytes."""
        if not self.file_path or not os.path.exists(self.file_path):
            return 0
        return os.path.getsize(self.file_path)
    
    def get_file_size_display(self):
        """Retorna o tamanho do arquivo formatado."""
        size = self.get_file_size()
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def delete(self, *args, **kwargs):
        """Remove o arquivo físico ao deletar o registro."""
        if self.file_path and os.path.exists(self.file_path):
            os.remove(self.file_path)
        super().delete(*args, **kwargs)

class PDFDownload(models.Model):
    """Modelo para armazenar informações de leads que baixam o PDF"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, verbose_name="Nome")
    email = models.EmailField(verbose_name="E-mail")
    company = models.CharField(max_length=100, blank=True, null=True, verbose_name="Empresa")
    role = models.CharField(max_length=100, blank=True, null=True, verbose_name="Cargo")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Telefone")
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    marketing_consent = models.BooleanField(default=False, verbose_name="Aceito receber comunicações de marketing")
    source = models.CharField(max_length=50, default="website", verbose_name="Origem do lead")
    user = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Usuário que realizou o download",
        related_name='pdf_downloads'
    )
    
    # Campos para controle do PDF
    pdf_file = models.FileField(
        upload_to='pdfs/manual_cyberseguranca/',
        verbose_name="Arquivo PDF",
        help_text="Arquivo PDF do manual",
        null=True,
        blank=True
    )
    download_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Número de downloads",
        help_text="Quantidade de vezes que o PDF foi baixado"
    )
    last_download = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Último download",
        help_text="Data e hora do último download"
    )
    
    class Meta:
        verbose_name = "Download de PDF"
        verbose_name_plural = "Downloads de PDF"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['created_at']),
            models.Index(fields=['marketing_consent']),
            models.Index(fields=['source']),
        ]

    def __str__(self):
        return f"{self.name} - {self.email}"

    def increment_download_count(self):
        """Incrementa o contador de downloads"""
        self.download_count += 1
        self.last_download = timezone.now()
        self.save()
