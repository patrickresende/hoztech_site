from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.hoztech.models import CookiePreference
import json
from datetime import datetime, timedelta
import os

class Command(BaseCommand):
    help = 'Exporta dados de cookies para um arquivo JSON'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            help='Caminho do arquivo de saída (opcional)'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Número de dias para exportar (padrão: 30)'
        )
        parser.add_argument(
            '--device-type',
            type=str,
            help='Filtrar por tipo de dispositivo (Mobile, Desktop, Tablet, Bot)'
        )
        parser.add_argument(
            '--browser',
            type=str,
            help='Filtrar por navegador'
        )
        parser.add_argument(
            '--performance',
            type=str,
            choices=['true', 'false'],
            help='Filtrar por cookies de performance'
        )
        parser.add_argument(
            '--marketing',
            type=str,
            choices=['true', 'false'],
            help='Filtrar por cookies de marketing'
        )

    def handle(self, *args, **options):
        try:
            # Prepara a query
            query = CookiePreference.objects.all()
            
            # Aplica filtros
            start_date = timezone.now() - timedelta(days=options['days'])
            query = query.filter(last_visit__gte=start_date)
            
            if options['device_type']:
                query = query.filter(device_type=options['device_type'])
            if options['browser']:
                query = query.filter(browser__icontains=options['browser'])
            if options['performance']:
                query = query.filter(performance_cookies=options['performance'] == 'true')
            if options['marketing']:
                query = query.filter(marketing_cookies=options['marketing'] == 'true')
            
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
            
            # Define o nome do arquivo
            if options['output']:
                filename = options['output']
            else:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'cookie_data_{timestamp}.json'
            
            # Cria o diretório de exportação se não existir
            export_dir = 'exports'
            if not os.path.exists(export_dir):
                os.makedirs(export_dir)
            
            # Caminho completo do arquivo
            filepath = os.path.join(export_dir, filename)
            
            # Salva o arquivo
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.stdout.write(
                self.style.SUCCESS(f'Dados exportados com sucesso para {filepath}')
            )
            self.stdout.write(f'Total de registros: {len(export_data)}')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Erro ao exportar dados: {str(e)}')
            ) 