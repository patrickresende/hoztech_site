import requests
import logging
import json
from typing import Dict, Optional, Tuple
from datetime import datetime
import socket
from user_agents import parse

logger = logging.getLogger(__name__)

class IPClientService:
    """Serviço para gerenciar informações de IP e localização do cliente"""
    
    @staticmethod
    def get_client_ip(request) -> str:
        """
        Obtém o IP real do cliente, considerando proxies e headers X-Forwarded-For
        """
        # Lista de headers que podem conter o IP real
        ip_headers = [
            'HTTP_X_FORWARDED_FOR',
            'HTTP_X_REAL_IP',
            'HTTP_CLIENT_IP',
            'HTTP_X_FORWARDED',
            'HTTP_FORWARDED_FOR',
            'HTTP_FORWARDED',
            'REMOTE_ADDR'
        ]
        
        for header in ip_headers:
            ip = request.META.get(header)
            if ip:
                # Se houver múltiplos IPs, pega o primeiro (cliente real)
                if ',' in ip:
                    ip = ip.split(',')[0].strip()
                if ip and ip != 'unknown':
                    return ip
        
        return request.META.get('REMOTE_ADDR', '0.0.0.0')

    @staticmethod
    def get_client_location(ip: str) -> Dict[str, str]:
        """
        Obtém informações detalhadas de localização do cliente usando ipapi.co
        Retorna um dicionário com informações de localização
        """
        try:
            # Primeira tentativa: ipapi.co
            response = requests.get(f'https://ipapi.co/{ip}/json/', timeout=5)
            if response.status_code == 200:
                data = response.json()
                return {
                    'city': data.get('city', 'Cidade desconhecida'),
                    'region': data.get('region', 'Região desconhecida'),
                    'country': data.get('country_name', 'País desconhecido'),
                    'country_code': data.get('country_code', ''),
                    'latitude': str(data.get('latitude', '0')),
                    'longitude': str(data.get('longitude', '0')),
                    'timezone': data.get('timezone', 'UTC'),
                    'isp': data.get('org', 'ISP desconhecido'),
                    'asn': data.get('asn', 'ASN desconhecido'),
                    'postal': data.get('postal', ''),
                    'continent': data.get('continent_code', ''),
                    'currency': data.get('currency', ''),
                    'currency_name': data.get('currency_name', ''),
                    'languages': data.get('languages', ''),
                    'calling_code': data.get('country_calling_code', ''),
                    'is_eu': data.get('in_eu', False),
                    'is_tor': data.get('tor', False),
                    'is_proxy': data.get('proxy', False),
                    'is_vpn': data.get('vpn', False),
                    'is_hosting': data.get('hosting', False),
                    'connection_type': data.get('connection', {}).get('type', ''),
                    'connection_asn': data.get('connection', {}).get('asn', ''),
                    'connection_isp': data.get('connection', {}).get('isp', ''),
                    'connection_org': data.get('connection', {}).get('organization', ''),
                    'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            
            # Segunda tentativa: ip-api.com (backup)
            response = requests.get(f'http://ip-api.com/json/{ip}', timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    return {
                        'city': data.get('city', 'Cidade desconhecida'),
                        'region': data.get('regionName', 'Região desconhecida'),
                        'country': data.get('country', 'País desconhecido'),
                        'country_code': data.get('countryCode', ''),
                        'latitude': str(data.get('lat', '0')),
                        'longitude': str(data.get('lon', '0')),
                        'timezone': data.get('timezone', 'UTC'),
                        'isp': data.get('isp', 'ISP desconhecido'),
                        'asn': data.get('as', 'ASN desconhecido'),
                        'postal': data.get('zip', ''),
                        'continent': '',
                        'currency': '',
                        'currency_name': '',
                        'languages': '',
                        'calling_code': '',
                        'is_eu': False,
                        'is_tor': False,
                        'is_proxy': False,
                        'is_vpn': False,
                        'is_hosting': False,
                        'connection_type': '',
                        'connection_asn': data.get('as', ''),
                        'connection_isp': data.get('isp', ''),
                        'connection_org': data.get('org', ''),
                        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao obter localização do IP {ip}: {str(e)}")
        except Exception as e:
            logger.error(f"Erro inesperado ao processar localização do IP {ip}: {str(e)}")
        
        # Retorna dados padrão em caso de erro
        return {
            'city': 'Localização desconhecida',
            'region': 'Região desconhecida',
            'country': 'País desconhecido',
            'country_code': '',
            'latitude': '0',
            'longitude': '0',
            'timezone': 'UTC',
            'isp': 'ISP desconhecido',
            'asn': 'ASN desconhecido',
            'postal': '',
            'continent': '',
            'currency': '',
            'currency_name': '',
            'languages': '',
            'calling_code': '',
            'is_eu': False,
            'is_tor': False,
            'is_proxy': False,
            'is_vpn': False,
            'is_hosting': False,
            'connection_type': '',
            'connection_asn': '',
            'connection_isp': '',
            'connection_org': '',
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    @staticmethod
    def get_browser_info(request) -> Dict[str, str]:
        """
        Obtém informações detalhadas do navegador do cliente
        """
        try:
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            ua = parse(user_agent)
            
            return {
                'browser': f"{ua.browser.family} {ua.browser.version_string}",
                'os': f"{ua.os.family} {ua.os.version_string}",
                'device': ua.device.family,
                'device_brand': ua.device.brand or '',
                'device_model': ua.device.model or '',
                'is_mobile': ua.is_mobile,
                'is_tablet': ua.is_tablet,
                'is_pc': ua.is_pc,
                'is_bot': ua.is_bot,
                'is_touch_capable': ua.is_touch_capable,
                'user_agent': user_agent
            }
        except Exception as e:
            logger.error(f"Erro ao processar informações do navegador: {str(e)}")
            return {
                'browser': 'Desconhecido',
                'os': 'Desconhecido',
                'device': 'Desconhecido',
                'device_brand': '',
                'device_model': '',
                'is_mobile': False,
                'is_tablet': False,
                'is_pc': False,
                'is_bot': False,
                'is_touch_capable': False,
                'user_agent': request.META.get('HTTP_USER_AGENT', '')
            }

    @staticmethod
    def get_connection_info(ip: str) -> Dict[str, str]:
        """
        Obtém informações adicionais sobre a conexão
        """
        try:
            # Tenta resolver o hostname
            hostname = socket.gethostbyaddr(ip)[0]
        except:
            hostname = 'Desconhecido'
            
        return {
            'hostname': hostname,
            'is_private': ip.startswith(('10.', '172.16.', '192.168.', '127.', '169.254.')),
            'is_loopback': ip.startswith('127.'),
            'is_link_local': ip.startswith('169.254.'),
            'is_multicast': ip.startswith(('224.', '239.')),
            'is_reserved': ip.startswith(('0.', '240.')),
            'protocol': 'IPv4' if '.' in ip else 'IPv6'
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
    def get_client_info(request) -> Tuple[str, Dict[str, str], Dict[str, str], Dict[str, str]]:
        """
        Obtém todas as informações do cliente em uma única chamada
        Retorna uma tupla com (ip, location_data, browser_info, connection_info)
        """
        ip = IPClientService.get_client_ip(request)
        location_data = IPClientService.get_client_location(ip)
        browser_info = IPClientService.get_browser_info(request)
        connection_info = IPClientService.get_connection_info(ip)
        
        return ip, location_data, browser_info, connection_info 