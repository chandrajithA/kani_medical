from .models import Cart_Item, Wishlist_Cart_Item

def common_data(request):

    if request.user.is_authenticated:
    
        cart_items = Cart_Item.objects.filter(cart__user=request.user)

        cart_items_count = sum(item.quantity for item in cart_items) if cart_items else 0

        wishlist_items_count = Wishlist_Cart_Item.objects.filter(wishlistcart__user=request.user).count()
    
    else:

        cart_items_count = 0
        wishlist_items_count = 0

    
    return {
        'cart_items_count':cart_items_count,
        'wishlist_items_count':wishlist_items_count
    }