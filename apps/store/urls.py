from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = "store"

urlpatterns = [
    path('', views.home, name='home'),
    path('categorias/', views.category_list, name='categories'),
    path('categoria/<slug:slug>/', views.category_detail, name='category_detail'),
    path('busca/', views.search, name='search'),
    
    # Cart URLs
    path('carrinho/', views.cart_detail, name='cart'),
    path('carrinho/adicionar/<int:product_id>/', views.cart_add, name='cart_add'),
    path('carrinho/remover/<int:product_id>/', views.cart_remove, name='cart_remove'),
    path('carrinho/atualizar/<int:product_id>/', views.cart_update, name='cart_update'),
    path('carrinho/limpar/', views.cart_clear, name='cart_clear'),
    
    # Authentication URLs
    path('login/', auth_views.LoginView.as_view(template_name='store/auth/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='store:home'), name='logout'),
    path('register/', views.register, name='register'),
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='store/auth/password_reset.html',
        email_template_name='store/auth/password_reset_email.html',
        subject_template_name='store/auth/password_reset_subject.txt'
    ), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='store/auth/password_reset_done.html'
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='store/auth/password_reset_confirm.html'
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='store/auth/password_reset_complete.html'
    ), name='password_reset_complete'),
    
    # Static Pages
    path('sobre/', views.about, name='about'),
    path('contato/', views.contact, name='contact'),
    path('termos/', views.terms, name='terms'),
    path('privacidade/', views.privacy, name='privacy'),
    path('produto/<int:pk>/', views.product_detail, name='product_detail'),
    path('perfil/', views.profile, name='profile'),
    path('perfil/pedidos/', views.orders, name='orders'),
] 