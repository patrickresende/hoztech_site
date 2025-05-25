from decimal import Decimal
from django.conf import settings
from .models import Product

class Cart:
    def __init__(self, request):
        """
        Inicializa o carrinho.
        """
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            # Salva um carrinho vazio na sessão
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart
    
    def add(self, product, quantity=1, override_quantity=False):
        """
        Adiciona um produto ao carrinho ou atualiza sua quantidade.
        """
        product_id = str(product.id)
        if product_id not in self.cart:
            self.cart[product_id] = {
                'quantity': 0,
                'price': str(product.current_price)
            }
        
        if override_quantity:
            self.cart[product_id]['quantity'] = quantity
        else:
            self.cart[product_id]['quantity'] += quantity
        
        self.save()
    
    def save(self):
        """
        Marca a sessão como modificada para garantir que seja salva.
        """
        self.session.modified = True
    
    def remove(self, product):
        """
        Remove um produto do carrinho.
        """
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()
    
    def update(self, product, quantity):
        """
        Atualiza a quantidade de um produto no carrinho.
        """
        self.add(product, quantity, override_quantity=True)
    
    def clear(self):
        """
        Remove todos os produtos do carrinho.
        """
        del self.session[settings.CART_SESSION_ID]
        self.save()
    
    def __iter__(self):
        """
        Itera sobre os itens no carrinho e obtém os produtos do banco de dados.
        """
        product_ids = self.cart.keys()
        # Obtém os objetos Product e adiciona-os ao carrinho
        products = Product.objects.filter(id__in=product_ids)
        cart = self.cart.copy()
        
        for product in products:
            cart[str(product.id)]['product'] = product
        
        for item in cart.values():
            item['price'] = Decimal(item['price'])
            item['total_price'] = item['price'] * item['quantity']
            yield item
    
    def get_total_price(self):
        """
        Calcula o custo total dos itens no carrinho.
        """
        return sum(Decimal(item['price']) * item['quantity'] for item in self.cart.values())
    
    def get_total_items(self):
        """
        Retorna o número total de itens no carrinho.
        """
        return sum(item['quantity'] for item in self.cart.values()) 