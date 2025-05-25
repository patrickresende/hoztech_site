from .models import Cart, CartItem

def cart(request):
    """
    Context processor that makes cart information available in all templates.
    """
    cart_items_count = 0
    cart_total = 0
    
    if request.user.is_authenticated:
        # Get cart for logged in user
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            cart_items_count = cart.items.count()
            cart_total = cart.total
    else:
        # Get cart from session for anonymous users
        session_cart = request.session.get('cart', {})
        cart_items_count = len(session_cart)
        cart_total = sum(quantity for quantity in session_cart.values())
    
    return {
        'cart_items_count': cart_items_count,
        'cart_total': cart_total,
    } 