from django.urls import path
from .views import *
from django.contrib.auth import views as auth_views
from .views import CustomPasswordResetView

urlpatterns = [
    path('', home_page, name='home_page'),
    path('products/', products_page, name='products_page'),
    path('products/<int:category_id>/', products_page, name='products_page'),
    path('products/add_to_cart/<int:product_id>/', add_to_cart, name='add_to_cart'),
    path('products/remove_from_cart/<int:product_id>/', remove_from_cart, name='remove_from_cart'),
    path('products/products_detail/<int:product_id>', product_detail_page, name='product_detail_page'),
    path('products/product_detail/increase_item_qty/<int:product_id>/', increase_cartitem_quantity, name='increase_cartitem_quantity'),
    path('products/product_detail/decrease_item_qty/<int:product_id>/', decrease_cartitem_quantity, name='decrease_cartitem_quantity'),
    path('products/product_detail/remove_or_buy/<int:product_id>/', removefromcart_or_buyproduct, name='removefromcart_or_buyproduct'),
    path('products/product_detail/add_or_buy/<int:product_id>/', addtocart_or_buyproduct, name='addtocart_or_buyproduct'),
    path('product/product_detail/submit_review/<int:product_id>/', submit_review, name='submit_review'),
    path('aboutUs/', aboutus_page, name='aboutus_page'),
    path('contactUs/', contactus_page, name='contactus_page'),
    path('user/cart/', cart_page, name='cart_page'),
    path('user/cart/increase_item_qty/<int:cart_item_id>/', increase_item_qty_in_cart, name='increase_item_qty_in_cart'),
    path('user/cart/decrease_item_qty/<int:cart_item_id>/', decrease_item_qty_in_cart, name='decrease_item_qty_in_cart'),
    path('user/cart/remove_or_buy/<int:cart_item_id>/', remove_or_buy_item_in_cart, name='remove_or_buy_item_in_cart'),
    path('user/cart/clear/', clearcart, name='clearcart'),
    path('user/cart/checkout/', checkout_page, name='checkout_page'),
    path('user/cart/checkout/product/<int:cart_item_id>/', checkout_page, name='checkout_page'),
    path('checkout/payment/initiate/<int:cart_item_id>/', initiate_payment, name='initiate_payment'),
    path('checkout/payment/initiate/', initiate_payment, name='initiate_payment'),
    path("checkout/payment/verification/", verify_payment, name="verify_payment"),
    path("user/payment/success/<int:order_id>/", payment_success_page, name="payment_success_page"),
    path("user/payment/failed/<int:order_id>/", payment_failed_page, name="payment_failed_page"),
    path("user/payment_cancel/<str:razorpay_order_id>/", payment_cancel, name="payment_cancel"),
    path("user/order/tracking/<int:order_id>/", order_tracking_page, name='order_tracking_page'),
    path("user/order/tracking/search/", order_search_page, name='order_search_page'),
    path('user/wishListCart/', wishlist_page, name='wishlist_page'),
    path('user/wishListCart/addProduct/<int:product_id>/', add_to_wishlistcart, name='add_to_wishlistcart'),
    path('user/wishListCart/removeProduct/<int:product_id>/', remove_from_wishlistcart, name='remove_from_wishlistcart'),
    path('user/wishListCart/clear/', clearwishlist, name='clearwishlist'),
    path('user/profile/', user_profile_page, name='user_profile_page'),
    path('user/profile/edit_details', user_profile_details_edit, name='user_profile_details_edit'),
    path('user/login/', user_login, name='user_login'),
    path('user/register/', user_register, name='user_register'),
    path('user/logout/', user_logout, name='user_logout'),
    path('reset_password/', CustomPasswordResetView.as_view(), name='password_reset'),
    path('reset_password_sent/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html'
    ), name='password_reset_done'),

    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html'
    ), name='password_reset_confirm'),

    path('reset_password_complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html'
    ), name='password_reset_complete'),
    
]