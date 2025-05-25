from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
import json
import csv
import os
import pandas as pd
import zipfile
from datetime import datetime
from .models import DataExport, CookieConsent, VisitorAccess

@shared_task
def process_export(export_id):
    """Processa exportação em background."""
    try:
        export = DataExport.objects.get(id=export_id)
        
        # Prepara query base
        if export.export_type == 'cookies':
            queryset = CookieConsent.objects.filter(
                timestamp__date__range=[export.date_range_start, export.date_range_end]
            )
        elif export.export_type == 'access':
            queryset = VisitorAccess.objects.filter(
                timestamp__date__range=[export.date_range_start, export.date_range_end]
            )
        else:  # all
            queryset = {
                'cookies': CookieConsent.objects.filter(
                    timestamp__date__range=[export.date_range_start, export.date_range_end]
                ),
                'access': VisitorAccess.objects.filter(
                    timestamp__date__range=[export.date_range_start, export.date_range_end]
                )
            }
        
        # Prepara dados para exportação
        if export.export_type == 'all':
            data = {
                'cookies': list(queryset['cookies'].values()),
                'access': list(queryset['access'].values())
            }
        else:
            data = list(queryset.values())
        
        # Cria diretório de exportações se não existir
        os.makedirs('exports', exist_ok=True)
        
        # Gera arquivo
        filename = f"export_{export.export_type}_{export.date_range_start}_{export.date_range_end}"
        if export.format == 'json':
            content = json.dumps(data, indent=2, default=str)
            filepath = f"exports/{filename}.json"
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
        elif export.format == 'csv':
            filepath = f"exports/{filename}.csv"
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                if export.export_type == 'all':
                    writer = csv.writer(f)
                    writer.writerow(['Tipo', 'Dados'])
                    for key, values in data.items():
                        writer.writerow([key, json.dumps(values, default=str)])
                else:
                    writer = csv.DictWriter(f, fieldnames=data[0].keys() if data else [])
                    writer.writeheader()
                    writer.writerows(data)
        elif export.format == 'xlsx':
            filepath = f"exports/{filename}.xlsx"
            if export.export_type == 'all':
                with pd.ExcelWriter(filepath) as writer:
                    for key, values in data.items():
                        df = pd.DataFrame(values)
                        df.to_excel(writer, sheet_name=key, index=False)
            else:
                df = pd.DataFrame(data)
                df.to_excel(filepath, index=False)
        
        # Comprime se solicitado
        if export.compress:
            zip_path = f"{filepath}.zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(filepath, os.path.basename(filepath))
            os.remove(filepath)  # Remove arquivo original
            filepath = zip_path
        
        # Atualiza registro de exportação
        export.file_path = filepath
        export.status = 'completed'
        export.save()
        
        # Notifica usuário por email
        if export.user.email:
            send_mail(
                subject='Exportação Concluída - Hoz Tech',
                message=f'''
                Sua exportação foi concluída com sucesso!
                
                Tipo: {export.export_type}
                Período: {export.date_range_start} a {export.date_range_end}
                Formato: {export.format}
                
                Você pode baixar o arquivo através do painel administrativo.
                ''',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[export.user.email],
                fail_silently=True
            )
        
        return True
        
    except Exception as e:
        if export:
            export.status = 'failed'
            export.error_message = str(e)
            export.save()
            
            # Notifica erro por email
            if export.user.email:
                send_mail(
                    subject='Erro na Exportação - Hoz Tech',
                    message=f'''
                    Ocorreu um erro ao processar sua exportação:
                    
                    Erro: {str(e)}
                    
                    Por favor, tente novamente ou entre em contato com o suporte.
                    ''',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[export.user.email],
                    fail_silently=True
                )
        
        raise  # Re-lança exceção para o Celery 