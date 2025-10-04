from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *

# Register your models here.
class CustomUserAdmin(UserAdmin):
    model = User_detail

    readonly_fields = ("last_login", "created_at")

    list_display = ( 'user_id', 'email', 'name', 'phone', 'gender','is_staff', 'is_active','is_superuser')

    list_filter = ('is_staff', 'is_active','is_superuser')

    search_fields = ('user_id', 'email', 'name', 'phone')
    
    ordering = ['id']
    
    fieldsets = (
        (None, {'fields': ('email', 'phone', 'password')}),
        ('Personal info', {'fields': ('name', 'user_profile_picture','gender','address','city', 'state', 'pincode')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ("Important dates", {"fields": ("last_login", "created_at")}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('name','email', 'phone', 'password1', 'password2', 'user_profile_picture','gender','address', 'city','pincode', 'is_active', 'is_staff', 'is_superuser'),
        }),
    )

admin.site.register(User_detail, CustomUserAdmin)






@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('category_name', 'category_background_color', 'created_at')
    search_fields = ('category_name',)
    list_filter = ('category_background_color',)
    ordering = ('category_name',)



@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'category', 'available_stock', 'product_price', 'discount', 'featured_option', 'rating', 'created_at')
    search_fields = ('product_name', 'category__category_name')
    list_filter = ('category', 'featured_option', 'created_at')
    ordering = ('-created_at',)



@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'rating_label', 'disable', 'posted_on')
    search_fields = ('product__product_name', 'user__name', 'user__email')
    list_filter = ('rating', 'disable', 'posted_on')
    ordering = ('-posted_on',)



# --------------------------
# WISHLIST & CART
# --------------------------


class WishlistCartItemInline(admin.TabularInline):
    model = Wishlist_Cart_Item
    extra = 1

@admin.register(Wishlist_Cart)
class WishlistCartAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at')
    inlines = [WishlistCartItemInline]
    search_fields = ('user__name', 'user__email')
    ordering = ('-created_at',)


class CartItemInline(admin.TabularInline):
    model = Cart_Item
    extra = 1

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at')
    inlines = [CartItemInline]
    search_fields = ('user__name', 'user__email')
    ordering = ('-created_at',)


# --------------------------
# ORDER & ORDER ITEM
# --------------------------
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    readonly_fields = ('product_name', 'category_name', 'unit_price', 'quantity')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user', 'status', 'delivery_status', 'order_payment_status', 'created_at', 'updated_at')
    search_fields = ('order_number', 'user__name', 'user__email')
    list_filter = ('status', 'delivery_status', 'order_payment_status', 'created_at')
    inlines = [OrderItemInline]
    ordering = ('-created_at',)



@admin.register(ShippingAddress)
class ShippingAddressAdmin(admin.ModelAdmin):
    list_display = ( 'get_order_number', 'firstname', 'lastname', 'phone', 'city', 'state', 'pincode')
    search_fields = ('order__order_number', 'firstname', 'lastname', 'phone', 'city')
    list_filter = ('city', 'state')
    ordering = ('order__created_at',)

    def get_order_number(self, obj):
        return obj.order.order_number
    get_order_number.short_description = 'Order Number'


# --------------------------
# ORDER ITEM
# --------------------------
@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'get_order_number', 'category_name', 'quantity', 'unit_price', 'total_discount_price')
    search_fields = ('product_name', 'order__order_number', 'category_name')
    ordering = ('order__created_at',)

    def get_order_number(self, obj):
        return obj.order.order_number
    get_order_number.short_description = 'Order Number'


# --------------------------
# PAYMENT
# --------------------------
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('razorpay_payment_id', 'order', 'method', 'amount', 'currency', 'status', 'captured', 'created_at')
    search_fields = ('razorpay_payment_id', 'order__order_number', 'method')
    list_filter = ('method', 'status', 'captured')
    ordering = ('-created_at',)


# --------------------------
# CONTACT US
# --------------------------
@admin.register(Contact_Us_Message)
class ContactUsAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'viewed', 'finished', 'pending', 'created_at')
    search_fields = ('name', 'email', 'message')
    list_filter = ('viewed', 'finished', 'pending', 'created_at')
    ordering = ('-created_at',)







