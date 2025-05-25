from .models import Category

def cart(request):
    """
    Context processor para o carrinho de compras.
    Adiciona o carrinho ao contexto de todos os templates.
    """
    cart = request.session.get('cart', {})
    cart_items_count = sum(item.get('quantity', 0) for item in cart.values())
    cart_total = sum(
        float(item.get('price', 0)) * item.get('quantity', 0)
        for item in cart.values()
    )
    
    return {
        'cart': cart,
        'cart_items_count': cart_items_count,
        'cart_total': cart_total,
    }

def categories(request):
    """
    Context processor para as categorias da loja.
    Adiciona a lista de categorias ativas ao contexto de todos os templates.
    """
    return {
        'categories': Category.objects.filter(is_active=True).order_by('name')
    } 