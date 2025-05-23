from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
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

class VisitorAccess(models.Model):
    """Modelo para registrar acessos de visitantes"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    endpoint = models.CharField(max_length=255)
    method = models.CharField(max_length=10)
    timestamp = models.DateTimeField(auto_now_add=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    isp = models.CharField(max_length=255, null=True, blank=True)
    browser = models.CharField(max_length=100, null=True, blank=True)
    os = models.CharField(max_length=100, null=True, blank=True)
    device_type = models.CharField(max_length=50, null=True, blank=True)
    session_id = models.CharField(max_length=100, null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['ip_address']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['session_id']),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.ip_address} - {self.timestamp}"

class CookieConsent(models.Model):
    """Modelo para registrar consentimentos de cookies"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visitor = models.ForeignKey(VisitorAccess, on_delete=models.CASCADE, related_name='cookie_consents')
    cookie_name = models.CharField(max_length=100)
    value = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    category = models.CharField(max_length=50, choices=[
        ('essential', 'Essencial'),
        ('performance', 'Desempenho'),
        ('marketing', 'Marketing'),
        ('analytics', 'Analytics')
    ])
    
    class Meta:
        indexes = [
            models.Index(fields=['cookie_name']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['category']),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.cookie_name} - {self.visitor.ip_address}"

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

    def __str__(self):
        return f"{self.user.username if self.user else 'Anonymous'} - {self.action}"

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
    
    class Meta:
        indexes = [
            models.Index(fields=['is_2fa_enabled']),
        ]

    def __str__(self):
        return f"Preferências de autenticação de {self.user.username}"

class DataExport(models.Model):
    """Modelo para registrar exportações de dados"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    export_type = models.CharField(max_length=50, choices=[
        ('cookies', 'Cookies'),
        ('access', 'Acessos'),
        ('all', 'Todos os Dados')
    ])
    date_range_start = models.DateTimeField()
    date_range_end = models.DateTimeField()
    file_path = models.CharField(max_length=255)
    status = models.CharField(max_length=50, choices=[
        ('pending', 'Pendente'),
        ('processing', 'Processando'),
        ('completed', 'Concluído'),
        ('failed', 'Falhou')
    ], default='pending')
    error_message = models.TextField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['export_type']),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.export_type} - {self.timestamp}"

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
        help_text="Data e hora do último download do PDF"
    )
    
    class Meta:
        verbose_name = "Download de PDF"
        verbose_name_plural = "Downloads de PDF"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['created_at']),
            models.Index(fields=['marketing_consent']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.email} ({self.created_at.strftime('%d/%m/%Y')})"
    
    def increment_download_count(self):
        """Incrementa o contador de downloads e atualiza a data do último download"""
        self.download_count += 1
        self.last_download = timezone.now()
        self.save(update_fields=['download_count', 'last_download'])
