from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Product, Category, Cart, CartItem, Order, OrderItem, Review

def get_categories():
    """Helper function to get all categories for the context"""
    return Category.objects.filter(is_active=True).order_by('name')

def home(request):
    """Home page view with featured products and categories"""
    context = {
        'categories': get_categories(),
        'featured_categories': Category.objects.filter(is_active=True, is_featured=True)[:3],
        'featured_products': Product.objects.filter(is_active=True, is_featured=True)[:6],
    }
    return render(request, 'store/home.html', context)

def product_list(request):
    """Product listing page with filtering and search"""
    products = Product.objects.filter(is_active=True)
    category_slug = request.GET.get('category')
    search_query = request.GET.get('q')
    
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug, is_active=True)
        products = products.filter(category=category)
    
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(products, 12)  # 12 products per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'categories': get_categories(),
        'products': page_obj,
        'current_category': category_slug,
        'search_query': search_query,
    }
    return render(request, 'store/product_list.html', context)

def product_detail(request, slug):
    """Product detail page with reviews and related products"""
    product = get_object_or_404(Product, slug=slug, is_active=True)
    related_products = Product.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(id=product.id)[:4]
    
    reviews = product.reviews.filter(is_active=True).order_by('-created_at')
    
    context = {
        'categories': get_categories(),
        'product': product,
        'related_products': related_products,
        'reviews': reviews,
    }
    return render(request, 'store/product_detail.html', context)

def category_detail(request, slug):
    """Category detail page with its products"""
    category = get_object_or_404(Category, slug=slug, is_active=True)
    products = Product.objects.filter(category=category, is_active=True)
    
    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'categories': get_categories(),
        'category': category,
        'products': page_obj,
    }
    return render(request, 'store/category_detail.html', context)

@login_required
def cart(request):
    """Shopping cart view"""
    cart, created = Cart.objects.get_or_create(user=request.user)
    context = {
        'categories': get_categories(),
        'cart': cart,
    }
    return render(request, 'store/cart.html', context)

@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart = request.session.get('cart', {})
    
    if str(product_id) in cart:
        cart[str(product_id)] += 1
    else:
        cart[str(product_id)] = 1
    
    request.session['cart'] = cart
    messages.success(request, f'{product.name} adicionado ao carrinho.')
    return redirect('store:cart')

@login_required
def remove_from_cart(request, product_id):
    cart = request.session.get('cart', {})
    if str(product_id) in cart:
        del cart[str(product_id)]
        request.session['cart'] = cart
        messages.success(request, 'Produto removido do carrinho.')
    return redirect('store:cart')

@login_required
def update_cart(request, product_id):
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        cart = request.session.get('cart', {})
        
        if quantity > 0:
            cart[str(product_id)] = quantity
        else:
            del cart[str(product_id)]
        
        request.session['cart'] = cart
        messages.success(request, 'Carrinho atualizado.')
    return redirect('store:cart')

@login_required
def checkout(request):
    """Checkout process view"""
    cart = get_object_or_404(Cart, user=request.user)
    if not cart.items.exists():
        messages.warning(request, 'Seu carrinho está vazio.')
        return redirect('store:cart')
    
    context = {
        'categories': get_categories(),
        'cart': cart,
    }
    return render(request, 'store/checkout.html', context)

@login_required
def orders(request):
    """User orders list"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    context = {
        'categories': get_categories(),
        'orders': orders,
    }
    return render(request, 'store/orders.html', context)

@login_required
def profile(request):
    """User profile view"""
    context = {
        'categories': get_categories(),
    }
    return render(request, 'store/profile.html', context)

def about(request):
    """About page"""
    context = {
        'categories': get_categories(),
    }
    return render(request, 'store/about.html', context)

def contact(request):
    """Contact page"""
    context = {
        'categories': get_categories(),
    }
    return render(request, 'store/contact.html', context)

def terms(request):
    """Terms of service page"""
    context = {
        'categories': get_categories(),
    }
    return render(request, 'store/terms.html', context)

def privacy(request):
    """Privacy policy page"""
    context = {
        'categories': get_categories(),
    }
    return render(request, 'store/privacy.html', context)

def search(request):
    """Search results view"""
    query = request.GET.get('q', '')
    if query:
        products = Product.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(category__name__icontains=query),
            is_active=True
        )
    else:
        products = Product.objects.none()
    
    context = {
        'categories': get_categories(),
        'products': products,
        'query': query,
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'store/includes/search_results.html', context)
    
    return render(request, 'store/search.html', context)
