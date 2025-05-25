from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
import uuid

class Category(models.Model):
    name = models.CharField(_('Nome'), max_length=100)
    slug = models.SlugField(_('Slug'), unique=True)
    description = models.TextField(_('Descrição'), blank=True)
    image = models.ImageField(_('Imagem'), upload_to='categories/', blank=True)
    parent = models.ForeignKey('self', verbose_name=_('Categoria Pai'), 
                              on_delete=models.CASCADE, null=True, blank=True, 
                              related_name='children')
    is_active = models.BooleanField(_('Ativa'), default=True)
    created_at = models.DateTimeField(_('Criado em'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Atualizado em'), auto_now=True)

    class Meta:
        verbose_name = _('Categoria')
        verbose_name_plural = _('Categorias')
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('store:category_detail', kwargs={'slug': self.slug})

class Product(models.Model):
    name = models.CharField(_('Nome'), max_length=200)
    slug = models.SlugField(_('Slug'), unique=True)
    sku = models.CharField(_('SKU'), max_length=50, unique=True)
    description = models.TextField(_('Descrição'))
    price = models.DecimalField(_('Preço'), max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(_('Preço Promocional'), max_digits=10, 
                                    decimal_places=2, null=True, blank=True)
    category = models.ForeignKey(Category, verbose_name=_('Categoria'), 
                                on_delete=models.CASCADE, related_name='products')
    stock = models.PositiveIntegerField(_('Estoque'), default=0)
    is_active = models.BooleanField(_('Ativo'), default=True)
    is_featured = models.BooleanField(_('Destaque'), default=False)
    created_at = models.DateTimeField(_('Criado em'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Atualizado em'), auto_now=True)

    class Meta:
        verbose_name = _('Produto')
        verbose_name_plural = _('Produtos')
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if not self.sku:
            self.sku = str(uuid.uuid4())[:8].upper()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('store:product_detail', kwargs={'slug': self.slug})

    @property
    def current_price(self):
        return self.sale_price if self.sale_price else self.price

class ProductImage(models.Model):
    product = models.ForeignKey(Product, verbose_name=_('Produto'), 
                               on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(_('Imagem'), upload_to='products/')
    is_primary = models.BooleanField(_('Imagem Principal'), default=False)
    order = models.PositiveIntegerField(_('Ordem'), default=0)
    created_at = models.DateTimeField(_('Criado em'), auto_now_add=True)

    class Meta:
        verbose_name = _('Imagem do Produto')
        verbose_name_plural = _('Imagens dos Produtos')
        ordering = ['order', '-is_primary']

    def __str__(self):
        return f"{self.product.name} - Imagem {self.order}"

class Cart(models.Model):
    user = models.ForeignKey(User, verbose_name=_('Usuário'), 
                            on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(_('ID da Sessão'), max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(_('Criado em'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Atualizado em'), auto_now=True)

    class Meta:
        verbose_name = _('Carrinho')
        verbose_name_plural = _('Carrinhos')

    def __str__(self):
        return f"Carrinho {self.id} - {self.user.username if self.user else 'Anônimo'}"

    @property
    def total(self):
        return sum(item.subtotal for item in self.items.all())

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, verbose_name=_('Carrinho'), 
                            on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, verbose_name=_('Produto'), 
                               on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(_('Quantidade'), default=1)
    created_at = models.DateTimeField(_('Criado em'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Atualizado em'), auto_now=True)

    class Meta:
        verbose_name = _('Item do Carrinho')
        verbose_name_plural = _('Itens do Carrinho')
        unique_together = ['cart', 'product']

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"

    @property
    def subtotal(self):
        return self.quantity * self.product.current_price

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', _('Pendente')),
        ('processing', _('Processando')),
        ('shipped', _('Enviado')),
        ('delivered', _('Entregue')),
        ('cancelled', _('Cancelado')),
    ]

    user = models.ForeignKey(User, verbose_name=_('Usuário'), 
                            on_delete=models.CASCADE)
    order_number = models.CharField(_('Número do Pedido'), max_length=50, unique=True)
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, 
                            default='pending')
    total_amount = models.DecimalField(_('Valor Total'), max_digits=10, decimal_places=2)
    shipping_address = models.TextField(_('Endereço de Entrega'))
    payment_method = models.CharField(_('Método de Pagamento'), max_length=50)
    payment_id = models.CharField(_('ID do Pagamento'), max_length=100, blank=True)
    notes = models.TextField(_('Observações'), blank=True)
    created_at = models.DateTimeField(_('Criado em'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Atualizado em'), auto_now=True)

    class Meta:
        verbose_name = _('Pedido')
        verbose_name_plural = _('Pedidos')
        ordering = ['-created_at']

    def __str__(self):
        return f"Pedido {self.order_number}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

class OrderItem(models.Model):
    order = models.ForeignKey(Order, verbose_name=_('Pedido'), 
                             on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, verbose_name=_('Produto'), 
                               on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(_('Quantidade'))
    price = models.DecimalField(_('Preço'), max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(_('Criado em'), auto_now_add=True)

    class Meta:
        verbose_name = _('Item do Pedido')
        verbose_name_plural = _('Itens do Pedido')

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"

    @property
    def subtotal(self):
        return self.quantity * self.price

class Review(models.Model):
    product = models.ForeignKey(Product, verbose_name=_('Produto'), 
                               on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, verbose_name=_('Usuário'), 
                            on_delete=models.CASCADE)
    rating = models.PositiveIntegerField(_('Avaliação'), 
                                       validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(_('Comentário'))
    is_approved = models.BooleanField(_('Aprovado'), default=False)
    created_at = models.DateTimeField(_('Criado em'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Atualizado em'), auto_now=True)

    class Meta:
        verbose_name = _('Avaliação')
        verbose_name_plural = _('Avaliações')
        ordering = ['-created_at']
        unique_together = ['product', 'user']

    def __str__(self):
        return f"Avaliação de {self.user.username} para {self.product.name}"
