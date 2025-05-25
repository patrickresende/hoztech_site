from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    path('', views.home, name='home'),
    path('produtos/', views.product_list, name='products'),
    path('produto/<slug:slug>/', views.product_detail, name='product_detail'),
    path('categoria/<slug:slug>/', views.category_detail, name='category_detail'),
    path('carrinho/', views.cart, name='cart'),
    path('carrinho/adicionar/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('carrinho/remover/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('carrinho/atualizar/<int:product_id>/', views.update_cart, name='update_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('pedidos/', views.order_list, name='orders'),
    path('pedido/<str:order_number>/', views.order_detail, name='order_detail'),
    path('perfil/', views.profile, name='profile'),
    path('sobre/', views.about, name='about'),
    path('contato/', views.contact, name='contact'),
    path('termos/', views.terms, name='terms'),
    path('privacidade/', views.privacy, name='privacy'),
    path('busca/', views.search, name='search'),
] 