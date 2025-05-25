# Hoztech Store

Loja virtual da Hoztech, especializada em produtos de tecnologia e informática.

## Requisitos

- Python 3.8+
- Django 5.2+
- PostgreSQL (recomendado) ou SQLite
- Redis (para cache e filas)
- Node.js e npm (para assets frontend)

## Instalação

1. Clone o repositório:
```bash
git clone https://github.com/seu-usuario/hoztech_site.git
cd hoztech_site
```

2. Crie e ative um ambiente virtual:
```bash
python -m venv .hoztech
.\.hoztech\Scripts\activate  # Windows
source .hoztech/bin/activate  # Linux/Mac
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Configure as variáveis de ambiente:
```bash
cp .env.example .env
# Edite o arquivo .env com suas configurações
```

5. Execute as migrações:
```bash
python manage.py migrate
```

6. Crie um superusuário:
```bash
python manage.py createsuperuser
```

7. Colete os arquivos estáticos:
```bash
python manage.py collectstatic
```

8. Inicie o servidor de desenvolvimento:
```bash
python manage.py runserver
```

## Estrutura do Projeto

```
hoztech_site/
├── apps/                    # Aplicações Django
│   ├── hoztech/            # Aplicação principal
│   └── store/              # Aplicação da loja
├── static/                  # Arquivos estáticos
│   ├── css/                # Estilos CSS
│   ├── js/                 # Scripts JavaScript
│   └── images/             # Imagens
├── templates/              # Templates HTML
├── media/                  # Arquivos de mídia
├── staticfiles/           # Arquivos estáticos coletados
└── manage.py              # Script de gerenciamento Django
```

## Funcionalidades

- Catálogo de produtos com categorias
- Carrinho de compras
- Sistema de pagamento integrado
- Área do cliente
- Gestão de pedidos
- Newsletter
- Busca de produtos
- Avaliações e comentários
- Sistema de cupons de desconto

## Desenvolvimento

1. Crie uma branch para sua feature:
```bash
git checkout -b feature/nova-funcionalidade
```

2. Faça commit das suas alterações:
```bash
git add .
git commit -m "Adiciona nova funcionalidade"
```

3. Envie para o repositório:
```bash
git push origin feature/nova-funcionalidade
```

## Produção

Para deploy em produção:

1. Configure as variáveis de ambiente de produção
2. Use um servidor WSGI (Gunicorn/uWSGI)
3. Configure um servidor web (Nginx/Apache)
4. Use um banco de dados PostgreSQL
5. Configure o Redis para cache
6. Use um serviço de armazenamento (AWS S3)
7. Configure SSL/TLS
8. Configure backups automáticos

## Licença

Este projeto é proprietário e confidencial. Todos os direitos reservados.

## Contato

Para mais informações, entre em contato:
- Email: contato@hoztech.com
- Site: https://hoztech.com
- WhatsApp: (XX) XXXX-XXXX 