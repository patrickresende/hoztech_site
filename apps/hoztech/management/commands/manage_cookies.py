from django.core.management.base import BaseCommand
from django.utils import timezone
from hoztech.models import CookiePreference, VisitorAccess, CookieConsent
from datetime import timedelta
import json
import os
from django.conf import settings

class Command(BaseCommand):
    help = 'Gerencia cookies em produção'

    def add_arguments(self, parser):
        parser.add_argument('--action', type=str, required=True,
                          choices=['list', 'export', 'cleanup', 'stats'],
                          help='Ação a ser executada')
        parser.add_argument('--days', type=int, default=30,
                          help='Número de dias para limpeza (padrão: 30)')
        parser.add_argument('--output', type=str,
                          help='Arquivo de saída para exportação')
        parser.add_argument('--category', type=str,
                          choices=['all', 'necessary', 'preferences', 'statistics', 'marketing'],
                          help='Categoria de cookies para filtrar')

    def handle(self, *args, **options):
        action = options['action']
        
        if action == 'list':
            self.list_cookies(options)
        elif action == 'export':
            self.export_cookies(options)
        elif action == 'cleanup':
            self.cleanup_cookies(options)
        elif action == 'stats':
            self.show_stats(options)

    def list_cookies(self, options):
        """Lista cookies com filtros"""
        query = CookiePreference.objects.all()
        
        if options['category'] and options['category'] != 'all':
            if options['category'] == 'necessary':
                query = query.filter(essential_cookies=True)
            elif options['category'] == 'preferences':
                query = query.filter(performance_cookies=True)
            elif options['category'] == 'statistics':
                query = query.filter(performance_cookies=True)
            elif options['category'] == 'marketing':
                query = query.filter(marketing_cookies=True)
        
        # Limita a 100 registros para não sobrecarregar
        cookies = query.order_by('-last_visit')[:100]
        
        self.stdout.write(self.style.SUCCESS(f'Total de registros: {query.count()}'))
        self.stdout.write('Últimos 100 registros:')
        
        for cookie in cookies:
            self.stdout.write(
                f"ID: {cookie.client_id} | "
                f"Performance: {cookie.performance_cookies} | "
                f"Marketing: {cookie.marketing_cookies} | "
                f"Última visita: {cookie.last_visit} | "
                f"País: {cookie.country or 'N/A'}"
            )

    def export_cookies(self, options):
        """Exporta cookies para arquivo JSON"""
        query = CookiePreference.objects.all()
        
        if options['category'] and options['category'] != 'all':
            if options['category'] == 'necessary':
                query = query.filter(essential_cookies=True)
            elif options['category'] == 'preferences':
                query = query.filter(performance_cookies=True)
            elif options['category'] == 'statistics':
                query = query.filter(performance_cookies=True)
            elif options['category'] == 'marketing':
                query = query.filter(marketing_cookies=True)
        
        data = []
        for cookie in query:
            data.append({
                'client_id': str(cookie.client_id),
                'performance': cookie.performance_cookies,
                'marketing': cookie.marketing_cookies,
                'last_visit': cookie.last_visit.isoformat(),
                'country': cookie.country,
                'city': cookie.city,
                'browser': cookie.browser,
                'os': cookie.os,
                'device_type': cookie.device_type,
                'change_history': cookie.change_history
            })
        
        # Define o arquivo de saída
        output_file = options['output'] or f'cookie_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        # Garante que o diretório existe
        os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
        
        # Salva o arquivo
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        self.stdout.write(self.style.SUCCESS(f'Exportado {len(data)} registros para {output_file}'))

    def cleanup_cookies(self, options):
        """Limpa cookies antigos"""
        days = options['days']
        old_date = timezone.now() - timedelta(days=days)
        
        # Conta registros antes da limpeza
        prefs_count = CookiePreference.objects.filter(last_visit__lt=old_date).count()
        visitors_count = VisitorAccess.objects.filter(created_at__lt=old_date).count()
        consents_count = CookieConsent.objects.filter(timestamp__lt=old_date).count()
        
        # Confirma com o usuário
        self.stdout.write(self.style.WARNING(
            f'Isso irá remover:\n'
            f'- {prefs_count} preferências de cookies\n'
            f'- {visitors_count} registros de visitantes\n'
            f'- {consents_count} consentimentos\n'
            f'Mais antigos que {days} dias.\n'
            f'Deseja continuar? (s/N): '
        ))
        
        if input().lower() != 's':
            self.stdout.write(self.style.ERROR('Operação cancelada'))
            return
        
        # Executa a limpeza
        CookiePreference.objects.filter(last_visit__lt=old_date).delete()
        VisitorAccess.objects.filter(created_at__lt=old_date).delete()
        CookieConsent.objects.filter(timestamp__lt=old_date).delete()
        
        self.stdout.write(self.style.SUCCESS(
            f'Limpeza concluída:\n'
            f'- {prefs_count} preferências removidas\n'
            f'- {visitors_count} visitantes removidos\n'
            f'- {consents_count} consentimentos removidos'
        ))

    def show_stats(self, options):
        """Mostra estatísticas de cookies"""
        # Estatísticas gerais
        total_prefs = CookiePreference.objects.count()
        total_visitors = VisitorAccess.objects.count()
        total_consents = CookieConsent.objects.count()
        
        # Estatísticas por categoria
        perf_count = CookiePreference.objects.filter(performance_cookies=True).count()
        marketing_count = CookiePreference.objects.filter(marketing_cookies=True).count()
        
        # Estatísticas por país
        country_stats = VisitorAccess.objects.values('country')\
            .annotate(total=models.Count('id'))\
            .order_by('-total')[:10]
        
        # Estatísticas por dispositivo
        device_stats = CookiePreference.objects.values('device_type')\
            .annotate(total=models.Count('id'))\
            .order_by('-total')
        
        self.stdout.write(self.style.SUCCESS('Estatísticas de Cookies:'))
        self.stdout.write(f'Total de preferências: {total_prefs}')
        self.stdout.write(f'Total de visitantes: {total_visitors}')
        self.stdout.write(f'Total de consentimentos: {total_consents}')
        self.stdout.write(f'\nPor categoria:')
        self.stdout.write(f'- Performance: {perf_count} ({perf_count/total_prefs*100:.1f}%)')
        self.stdout.write(f'- Marketing: {marketing_count} ({marketing_count/total_prefs*100:.1f}%)')
        
        self.stdout.write(f'\nTop 10 países:')
        for stat in country_stats:
            self.stdout.write(f"- {stat['country'] or 'Desconhecido'}: {stat['total']}")
        
        self.stdout.write(f'\nDispositivos:')
        for stat in device_stats:
            self.stdout.write(f"- {stat['device_type'] or 'Desconhecido'}: {stat['total']}") 