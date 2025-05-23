from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from .models import PDFDownload

@admin.register(PDFDownload)
class PDFDownloadAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'company', 'created_at', 'download_count', 'marketing_consent', 'user')
    list_filter = ('marketing_consent', 'source', 'created_at', 'user')
    search_fields = ('name', 'email', 'company', 'role', 'phone', 'user__username')
    readonly_fields = ('id', 'created_at', 'last_download', 'download_count', 'ip_address', 'user_agent', 'user')
    fieldsets = (
        (_('Informações do Lead'), {
            'fields': ('name', 'email', 'company', 'role', 'phone', 'marketing_consent', 'source')
        }),
        (_('Status do Download'), {
            'fields': ('pdf_file', 'download_count', 'last_download', 'user')
        }),
        (_('Informações Técnicas'), {
            'fields': ('id', 'created_at', 'ip_address', 'user_agent'),
            'classes': ('collapse',)
        })
    )
    
    def has_add_permission(self, request):
        return False  # Impede a criação manual de registros
    
    def has_delete_permission(self, request, obj=None):
        return False  # Impede a exclusão de registros
    
    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions
    
    def get_model_perms(self, request):
        # Garante que o modelo aparece no menu do admin
        perms = super().get_model_perms(request)
        perms['view'] = True
        return perms
    
    def get_queryset(self, request):
        # Exibe todos os downloads realizados
        return super().get_queryset(request)
    
    def changelist_view(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}
        extra_context['title'] = _('Downloads realizados')
        return super().changelist_view(request, extra_context=extra_context)
    
    def get_fieldsets(self, request, obj=None):
        # Personaliza o título da página de edição
        fieldsets = super().get_fieldsets(request, obj)
        return fieldsets
    
    def get_form(self, request, obj=None, **kwargs):
        # Impede edição
        form = super().get_form(request, obj, **kwargs)
        for field in form.base_fields:
            form.base_fields[field].disabled = True
        return form

# Adiciona uma seção de downloads realizados ao UserAdmin
class PDFDownloadInline(admin.TabularInline):
    model = PDFDownload
    fields = ('name', 'email', 'company', 'created_at', 'download_count', 'last_download')
    readonly_fields = fields
    extra = 0
    can_delete = False
    max_num = 0
    show_change_link = True
    verbose_name = "Download realizado"
    verbose_name_plural = "Downloads realizados"
    
    def has_add_permission(self, request, obj=None):
        return False

# Registra o UserAdmin personalizado
admin.site.unregister(User)
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    inlines = list(UserAdmin.inlines) + [PDFDownloadInline]
    list_display = list(UserAdmin.list_display) + ['get_download_count']
    
    def get_download_count(self, obj):
        return obj.pdf_downloads.count()
    get_download_count.short_description = "Downloads realizados"
    get_download_count.admin_order_field = 'pdf_downloads__count'
