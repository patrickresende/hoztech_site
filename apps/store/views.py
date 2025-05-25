from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Category, Product, Order
from .cart import Cart
from django.http import Http404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model

def home(request):
    """Página inicial da loja"""
    # Obtém categorias em destaque (as 4 primeiras categorias)
    featured_categories = Category.objects.filter(is_active=True)[:4]
    
    # Obtém produtos em destaque (os 8 produtos mais recentes)
    featured_products = Product.objects.filter(
        is_active=True,
        stock__gt=0
    ).order_by('-created_at')[:8]
    
    return render(request, 'store/home.html', {
        'title': 'Loja Hoztech - Sua Loja de Tecnologia',
        'description': 'Encontre as melhores soluções em tecnologia para impulsionar seu negócio.',
        'featured_categories': featured_categories,
        'featured_products': featured_products,
    })

def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    products = Product.objects.filter(category=category, is_active=True)
    
    context = {
        'category': category,
        'products': products,
    }
    return render(request, 'store/category_detail.html', context)

def search(request):
    query = request.GET.get('q', '')
    category = request.GET.get('category')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    sort = request.GET.get('sort', '-created_at')
    
    products = Product.objects.filter(is_active=True)
    
    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(sku__icontains=query)
        )
    
    if category:
        products = products.filter(category__slug=category)
    
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)
    
    # Ordenação
    if sort == 'price':
        products = products.order_by('price')
    elif sort == '-price':
        products = products.order_by('-price')
    elif sort == 'name':
        products = products.order_by('name')
    elif sort == '-name':
        products = products.order_by('-name')
    else:  # default: newest first
        products = products.order_by('-created_at')
    
    categories = Category.objects.filter(is_active=True)
    
    context = {
        'products': products,
        'categories': categories,
        'query': query,
        'selected_category': category,
        'min_price': min_price,
        'max_price': max_price,
        'sort': sort,
    }
    return render(request, 'store/search.html', context)

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Conta criada com sucesso! Bem-vindo à Hoztech Store.')
            return redirect('store:home')
    else:
        form = UserCreationForm()
    
    return render(request, 'store/auth/register.html', {'form': form})

# Cart Views
def cart_detail(request):
    cart = Cart(request)
    return render(request, 'store/cart/detail.html', {'cart': cart})

@require_POST
def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id, is_active=True)
    quantity = int(request.POST.get('quantity', 1))
    
    if quantity > 0:
        cart.add(product=product, quantity=quantity)
        messages.success(request, f'Produto "{product.name}" adicionado ao carrinho.')
    else:
        messages.error(request, 'Quantidade inválida.')
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'cart_items_count': cart.get_total_items(),
            'cart_total': cart.get_total_price(),
            'message': f'Produto "{product.name}" adicionado ao carrinho.'
        })
    
    return redirect('store:cart')

@require_POST
def cart_remove(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    messages.success(request, f'Produto "{product.name}" removido do carrinho.')
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'cart_items_count': cart.get_total_items(),
            'cart_total': cart.get_total_price(),
            'message': f'Produto "{product.name}" removido do carrinho.'
        })
    
    return redirect('store:cart')

@require_POST
def cart_update(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id, is_active=True)
    quantity = int(request.POST.get('quantity', 1))
    
    if quantity > 0:
        cart.update(product=product, quantity=quantity)
        messages.success(request, f'Quantidade do produto "{product.name}" atualizada.')
    else:
        cart.remove(product)
        messages.success(request, f'Produto "{product.name}" removido do carrinho.')
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'cart_items_count': cart.get_total_items(),
            'cart_total': cart.get_total_price(),
            'message': f'Quantidade do produto "{product.name}" atualizada.'
        })
    
    return redirect('store:cart')

@require_POST
def cart_clear(request):
    cart = Cart(request)
    cart.clear()
    messages.success(request, 'Carrinho esvaziado.')
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'cart_items_count': 0,
            'cart_total': 0,
            'message': 'Carrinho esvaziado.'
        })
    
    return redirect('store:cart')

# Static Pages
def about(request):
    """Página Sobre Nós"""
    return render(request, 'store/static/about.html', {
        'title': 'Sobre Nós - Hoztech Store',
        'description': 'Conheça mais sobre a Hoztech Store, sua loja de tecnologia e informática.'
    })

def contact(request):
    """Página de Contato"""
    return render(request, 'store/static/contact.html', {
        'title': 'Contato - Hoztech Store',
        'description': 'Entre em contato com a Hoztech Store. Estamos aqui para ajudar!'
    })

def terms(request):
    """Termos de Uso"""
    return render(request, 'store/static/terms.html', {
        'title': 'Termos de Uso - Hoztech Store',
        'description': 'Termos e condições de uso da Hoztech Store.'
    })

def privacy(request):
    """Política de Privacidade"""
    return render(request, 'store/static/privacy.html', {
        'title': 'Política de Privacidade - Hoztech Store',
        'description': 'Política de privacidade da Hoztech Store.'
    })

def category_list(request):
    """Lista todas as categorias ativas"""
    categories = Category.objects.filter(is_active=True)
    
    return render(request, 'store/category_list.html', {
        'title': 'Categorias - Hoztech Store',
        'description': 'Explore nossas categorias de produtos.',
        'categories': categories,
    })

def product_detail(request, pk):
    """Exibe os detalhes de um produto"""
    try:
        product = Product.objects.select_related('category').prefetch_related('images').get(
            pk=pk,
            is_active=True
        )
    except Product.DoesNotExist:
        raise Http404("Produto não encontrado")
    
    return render(request, 'store/product_detail.html', {
        'title': f'{product.name} - Hoztech Store',
        'description': product.description[:160] if product.description else '',
        'product': product
    })

def profile(request):
    """Exibe o perfil do usuário autenticado"""
    user = request.user
    return render(request, 'store/auth/profile.html', {'user': user})

@login_required
def orders(request):
    """Lista os pedidos do usuário autenticado"""
    pedidos = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'store/auth/orders.html', {'orders': pedidos}) 