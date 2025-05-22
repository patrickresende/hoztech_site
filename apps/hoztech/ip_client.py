import requests
import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class IPClientService:
    """Serviço para gerenciar informações de IP e localização do cliente"""
    
    @staticmethod
    def get_client_ip(request) -> str:
        """
        Obtém o IP real do cliente, considerando proxies e headers X-Forwarded-For
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # Pega o primeiro IP da lista (cliente real)
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
        return ip

    @staticmethod
    def get_client_location(ip: str) -> Dict[str, str]:
        """
        Obtém informações detalhadas de localização do cliente usando ipapi.co
        Retorna um dicionário com informações de localização
        """
        try:
            response = requests.get(f'https://ipapi.co/{ip}/json/', timeout=5)
            if response.status_code == 200:
                data = response.json()
                return {
                    'city': data.get('city', 'Cidade desconhecida'),
                    'region': data.get('region', 'Região desconhecida'),
                    'country': data.get('country_name', 'País desconhecido'),
                    'latitude': str(data.get('latitude', '0')),
                    'longitude': str(data.get('longitude', '0')),
                    'timezone': data.get('timezone', 'UTC'),
                    'isp': data.get('org', 'ISP desconhecido'),
                    'asn': data.get('asn', 'ASN desconhecido')
                }
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao obter localização do IP {ip}: {str(e)}")
        except Exception as e:
            logger.error(f"Erro inesperado ao processar localização do IP {ip}: {str(e)}")
        
        return {
            'city': 'Localização desconhecida',
            'region': 'Região desconhecida',
            'country': 'País desconhecido',
            'latitude': '0',
            'longitude': '0',
            'timezone': 'UTC',
            'isp': 'ISP desconhecido',
            'asn': 'ASN desconhecido'
        }

    @staticmethod
    def format_location_string(location_data: Dict[str, str]) -> str:
        """
        Formata os dados de localização em uma string legível
        """
        location_parts = []
        
        if location_data['city'] != 'Localização desconhecida':
            location_parts.append(location_data['city'])
        if location_data['region'] != 'Região desconhecida':
            location_parts.append(location_data['region'])
        if location_data['country'] != 'País desconhecido':
            location_parts.append(location_data['country'])
            
        return ', '.join(location_parts) if location_parts else 'Localização desconhecida'

    @staticmethod
    def get_client_info(request) -> Tuple[str, Dict[str, str]]:
        """
        Obtém todas as informações do cliente em uma única chamada
        Retorna uma tupla com (ip, location_data)
        """
        ip = IPClientService.get_client_ip(request)
        location_data = IPClientService.get_client_location(ip)
        return ip, location_data 