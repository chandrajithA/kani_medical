from django.shortcuts import render, redirect
from .models import *
from django.contrib import messages
from django.contrib.auth import login, logout
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
import re
from django.db.models import Q, F, ExpressionWrapper, FloatField
from .static_content_utils import *
from django.contrib.auth.views import PasswordResetView
from .forms import RateLimitedPasswordResetForm
from django.views.decorators.http import require_POST
from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
import razorpay
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.http import JsonResponse
import hmac, hashlib
from django.db.models import Avg
from django.db.models import Count, Case, When, IntegerField



DELIVERY_CHARGE_BILLVALUE = Decimal("500")
DELIVERY_AMOUNT = Decimal("100")

# Create your views here.
def home_page(request):
    categories = Category.objects.all().order_by('-created_at')
    products = Product.objects.filter(
                    Q(featured_option='Discount') |
                    Q(featured_option='New') |
                    Q(featured_option='Bestseller')
                )
    cart_items = Cart_Item.objects.filter(cart__user=request.user) if request.user.is_authenticated else []
    cart_dict = {item.product_id for item in cart_items}

    wishlist_items = Wishlist_Cart_Item.objects.filter(wishlistcart__user=request.user) if request.user.is_authenticated else []
    wishlist_dict = {item.product_id for item in wishlist_items}

    context = {
        'categories':categories,
        'products':products,
        'cart_dict':cart_dict,
        'wishlist_dict':wishlist_dict,
    }
    return render(request, 'home_page.html', context)





def products_page(request, category_id=None):
    categories = Category.objects.all().order_by('category_name')
    sort_option = request.GET.get('sort', 'recommended')
    

    selected_category_name = None

    if category_id:
        products = Product.objects.select_related('category').filter(category__id=category_id)
        selected_category = Category.objects.filter(id=category_id).first()
        if selected_category:
            selected_category_name = selected_category.category_name
    else:
        products = Product.objects.select_related('category').all()

    # 👇 Annotate discounted_price (calculated: price - (price * discount / 100))
    products = products.annotate(
        annotated_discounted_price=ExpressionWrapper(
            F('product_price') - (F('product_price') * F('discount') / 100.0),
            output_field=FloatField()
        )
    )

    if sort_option == 'price_low_to_high':
        products = products.order_by('annotated_discounted_price')
    elif sort_option == 'price_high_to_low':
        products = products.order_by('-annotated_discounted_price')
    elif sort_option == 'offer_low_to_high':
        products = products.order_by('discount')
    elif sort_option == 'offer_high_to_low':
        products = products.order_by('-discount')
    else:
        # Recommended or default sorting (e.g. by created date)
        products = products.order_by('-created_at')

    cart_items = Cart_Item.objects.filter(cart__user=request.user) if request.user.is_authenticated else []
    cart_dict = {item.product_id for item in cart_items}

    wishlist_items = Wishlist_Cart_Item.objects.filter(wishlistcart__user=request.user) if request.user.is_authenticated else []
    wishlist_dict = {item.product_id for item in wishlist_items}

    
    context = {
        'categories':categories,
        'products':products,
        'selected_category_id':category_id,
        'selected_category_name':selected_category_name,
        'selected_sort_option': sort_option,
        'cart_dict':cart_dict,
        'wishlist_dict':wishlist_dict,
    }
    return render(request, 'products_page.html', context)


    



def product_detail_page(request, product_id):

    if request.user.is_authenticated:
        productincart = Cart_Item.objects.select_related('cart','product').filter(cart__user=request.user, product__id=product_id).first()
    else:
        productincart = []


    product = Product.objects.select_related('category').filter(id=product_id).first()
    related_products=Product.objects.select_related('category').filter(category__id=product.category.id).exclude(id=product_id).all()

    reviews = product.review.select_related('user').all()
    product.rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
    product.save(update_fields=['rating'])

    review_count = reviews.count()

    ratings_data = reviews.aggregate(
        total=Count('id'),
        rating1=Count(Case(When(rating=1, then=1), output_field=IntegerField())),
        rating2=Count(Case(When(rating=2, then=1), output_field=IntegerField())),
        rating3=Count(Case(When(rating=3, then=1), output_field=IntegerField())),
        rating4=Count(Case(When(rating=4, then=1), output_field=IntegerField())),
        rating5=Count(Case(When(rating=5, then=1), output_field=IntegerField())),
    )

    rating_percentages = {}
    total = ratings_data['total'] or 0
    for star in range(1, 6):
        count = ratings_data[f'rating{star}']
        rating_percentages[star] = (count / total * 100) if total else 0

    cart_items = Cart_Item.objects.filter(cart__user=request.user) if request.user.is_authenticated else []
    cart_dict = {item.product_id for item in cart_items}

    wishlist_items = Wishlist_Cart_Item.objects.filter(wishlistcart__user=request.user) if request.user.is_authenticated else []
    wishlist_dict = {item.product_id for item in wishlist_items}

    context = {
        'product':product,
        'products':related_products,
        'productincart':productincart,
        'reviews':reviews,
        'ratings_data':ratings_data,
        'review_count':review_count,
        'rating_percentages':rating_percentages,
        'cart_dict':cart_dict,
        'wishlist_dict':wishlist_dict,

    }
    return render(request, 'product_detail_page.html', context)




def submit_review(request, product_id):
    if request.method=="POST":
        if request.user.is_authenticated:
            product = Product.objects.filter(id=product_id).first()
            rating = int(request.POST.get('rating'))  # Get rating from form
            comment = request.POST.get('comment', '').strip()
                    
            if not (1 <= rating <= 5):
                messages.error(request, "Please select a valid rating.")
                return redirect('product_detail_page', product_id=product_id)

            # Check if user already submitted review
            # review, created = Review.objects.get_or_create(product=product, user=user,defaults={'rating': rating, 'comment': comment})

            review = product.review.filter(user=request.user).first()

            if review is None:
                # Create new review
                Review.objects.create(
                    product=product,
                    user=request.user,
                    rating=rating,
                    comment=comment
                )
                messages.success(request, "Your review was submitted successfully.")
                return redirect('product_detail_page', product_id=product_id)
            else:
                # Edit existing review
                review.rating = rating
                review.comment = comment
                review.save()
                messages.success(request, "Your review was updated successfully.")
                return redirect('product_detail_page', product_id=product_id)
        else:
            messages.error(request, "Kindly login and again submit the review")
            return redirect('product_detail_page', product_id=product_id)




@login_required
def add_to_cart(request, product_id):
    next_url = request.GET.get('next')

    selected_product = Product.objects.select_related('category').filter(id=product_id).first()
    cart, _ = Cart.objects.get_or_create(user=request.user)
    quantity = 1
    addtocart(cart, selected_product, quantity, selected_product.available_stock)
    return redirect(next_url)

    



@login_required
def remove_from_cart(request, product_id):
    next_url = request.GET.get('next')

    selected_cart_item = Cart_Item.objects.filter(cart__user=request.user, product__id=product_id).first()
    selected_cart_item.delete()
    return redirect(next_url)




@login_required
@require_POST
def increase_cartitem_quantity(request, product_id):

    cart_item = Cart_Item.objects.select_related('cart','product').filter(cart__user=request.user, product__id=product_id).first()

    if cart_item and cart_item.quantity < cart_item.product.available_stock :
        cart_item.quantity += 1
        cart_item.save(update_fields=['quantity'])
        return redirect('product_detail_page', product_id=product_id)
    else:
        messages.error(request, f"'{cart_item.product.product_name}' has only {cart_item.product.available_stock} items available.")
        return redirect('product_detail_page', product_id=product_id)
        
    

@login_required
@require_POST
def decrease_cartitem_quantity(request, product_id):
    
    cart_item = Cart_Item.objects.filter(cart__user=request.user, product__id=product_id).first()
       
    if cart_item and cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save(update_fields=['quantity'])
        return redirect('product_detail_page', product_id=product_id)
        
    elif cart_item.quantity == 1:
        messages.error(request, "Product value cannot be Zero.")
        return redirect('product_detail_page', product_id=product_id)


        
 
def addtocart_or_buyproduct(request, product_id):
    if request.method=="POST":
        if request.user.is_authenticated:
            quantity = request.POST.get('quantity')
            action = request.POST.get('action')
            
            selected_product = Product.objects.filter(id=product_id).first()
            
            cart, _ = Cart.objects.get_or_create(user=request.user)

            cart_item = addtocart(cart, selected_product, quantity, selected_product.available_stock)

            if cart_item:
                if action == "buy_now":
                    return redirect('checkout_page', cart_item_id=cart_item.id)
                elif action == "add_to_cart":
                    messages.success(request, f"'{cart_item.product.product_name}' added to cart.")
                    return redirect('product_detail_page', product_id=product_id) 
                
            else:
                messages.error(request, f"{selected_product.product_name} has only {selected_product.available_stock} items available.")
                return redirect('product_detail_page', product_id=product_id)
            
        else:
            messages.error(request, "Kindly login to add or buy products.")
            return redirect('product_detail_page', product_id=product_id)


def addtocart(cart, selected_product, quantity, available_stock):

    if cart and selected_product  and quantity:
        quantity = int(quantity)
        
        if quantity <= available_stock:
            cart_item = Cart_Item.objects.create(
                cart=cart,
                product=selected_product,
                quantity=quantity
            )
            cart_item.save()
            return cart_item
        else:
            return []
    




@login_required
@require_POST
def removefromcart_or_buyproduct(request, product_id):

    action = request.POST.get('action')

    selected_product = Cart_Item.objects.filter(cart__user=request.user, product__id=product_id).first()

    if action == "remove_from_cart":
        selected_product.delete()
        messages.success(request, f"'{selected_product.product.product_name}' is removed from the cart.")
        return redirect('product_detail_page', product_id=product_id)

    elif action == "buy_now":
        return redirect('checkout_page', cart_item_id=selected_product.id)



def aboutus_page(request):
    return render(request, 'aboutus_page.html')



def contactus_page(request):
    if request.method == 'GET':
        prefill = request.session.pop('contactusprefill', None)
        context = {
            'prefill':prefill,
        }
        return render(request, 'contactus_page.html', context)
    
    elif request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')

        valid = True

        if not name.strip():
            messages.error(request, "Name cannot be empty or spaces only.")
            valid = False
        elif not re.fullmatch(r'[A-Za-z ]+', name):
            messages.error(request, "Name can only contain letters and spaces.")
            valid = False
        elif len(re.sub(r'[^A-Za-z]', '', name)) < 4:
            messages.error(request, "Name must contain at least 4 letters.")
            valid = False

        if not re.fullmatch(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$', email):
            messages.error(request, "Enter a valid email address.")
            valid = False

        if not message.strip():
            messages.error(request, "Message cannot be empty or spaces only.")
            valid = False

        if valid:
            
            # Create user
            Contact_Us_Message.objects.create(
                name=name,
                email=email,
                message=message,
            )
            
            messages.success(request, "Message sent successfully! We'll respond soon.")
            return redirect('contactus_page')
        else:
            prefill = {
                'name': name,
                'email': email,
                "message": message,
            }

            request.session['contactusprefill'] = prefill
            return redirect('contactus_page')
        


@login_required
def cart_page(request):
    cart_items=Cart_Item.objects.select_related('cart','product').filter(cart__user=request.user).all()

    total_amount = sum(item.get_total_price for item in cart_items)
    total_discount_price = sum(item.get_total_discount_price for item in cart_items)
    discount_price = total_amount - total_discount_price

    
    if total_amount < Decimal(DELIVERY_CHARGE_BILLVALUE):
        delivery_charge = Decimal(DELIVERY_AMOUNT)
    else:
        delivery_charge = Decimal("0")

    total_amount_to_pay = total_discount_price + delivery_charge

    context = {
        'cart_items':cart_items,
        'total_amount':total_amount,
        'total_discount_price':total_discount_price,
        'discount_price':discount_price,
        'delivery_charge':delivery_charge,
        'total_amount_to_pay':total_amount_to_pay,

    }
    return render(request, 'cart_page.html', context)


@login_required
@require_POST
def increase_item_qty_in_cart(request, cart_item_id):

    cart_item = Cart_Item.objects.select_related('cart','product').filter(cart__user=request.user, product__id=cart_item_id).first()

    if cart_item and cart_item.quantity < cart_item.product.available_stock:
        cart_item.quantity += 1
        cart_item.save()
        return redirect('cart_page')
    
    else:
        messages.error(request, f"'{cart_item.product.product_name}' has only {cart_item.product.available_stock} items available.")
        return redirect('cart_page')
        
        



@login_required
@require_POST
def decrease_item_qty_in_cart(request, cart_item_id):
    
    cart_item = Cart_Item.objects.filter(cart__user=request.user, product__id=cart_item_id).first()
    
    if cart_item and cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save()
        return redirect('cart_page')
        
    elif cart_item.quantity == 1:
        messages.error(request, "Product value cannot be Zero.")
        return redirect('cart_page')
        
    


@login_required
@require_POST
def remove_or_buy_item_in_cart(request, cart_item_id):

    action = request.POST.get('action')
    
    selected_product = Cart_Item.objects.filter(cart__user=request.user, product__id=cart_item_id).first()

    if action == "remove_from_cart":
        selected_product.delete()
        messages.success(request, f"'{selected_product.product.product_name}' is removed from the cart.")
        return redirect('cart_page')

    if action == "buy_now":
        return redirect('checkout_page', cart_item_id=selected_product.id)
    



@login_required
def clearcart(request):

    cart = Cart.objects.filter(user=request.user).first()
    if cart:
        cart.delete()
        messages.success(request, f"'{request.user.name}' cart cleared successfully.")
        return redirect('cart_page')
    

    
    
def _to_paise_rupees_decimal(amount_rupees):
    # safe conversion to paise (int) from rupees
    return int((Decimal(str(amount_rupees)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    

@login_required
def checkout_page(request, cart_item_id=None):
    cart = Cart.objects.filter(user=request.user).first()

    # Handle case: cart doesn't exist
    if not cart:
        return redirect('home_page')

    # Full cart
    if cart_item_id is None:
        cart_items = Cart_Item.objects.select_related('cart','product').filter(cart=cart)
        if not cart_items:
            return redirect('cart_page')
    else:
        # Single item
        cart_items = Cart_Item.objects.select_related('cart','product').filter(cart=cart, id=cart_item_id)
        if not cart_items:
            return redirect('cart_page')

    bill_amount = sum(item.get_total_price for item in cart_items)
    total_amount = sum(item.get_total_discount_price for item in cart_items)
    discount_amount = bill_amount - total_amount
    delivery_charge = Decimal(DELIVERY_AMOUNT) if total_amount < Decimal(DELIVERY_CHARGE_BILLVALUE) else Decimal("0")
    final_amount = total_amount + delivery_charge              
    final_amount_paise = _to_paise_rupees_decimal(final_amount)

    # ✅ Add user details to context
    user = request.user
    user_data = {
        "firstname": getattr(user, "name", ""),
        "email": getattr(user, "email", ""),
        "phone": getattr(user, "phone", ""),
        "address": getattr(user, "address", ""),
        "city": getattr(user, "city", ""),
        "state": getattr(user, "state", ""),
        "pincode": getattr(user, "pincode", ""),
    }
        
    # GET – just show the page
    context = {
        "cart_items": cart_items,
        "bill_amount":bill_amount,
        "total_amount": total_amount,
        "delivery_charge": delivery_charge,
        'discount_amount':discount_amount,
        "final_amount": final_amount,
        "final_amount_pay": final_amount_paise,
        'cart_item_id':cart_item_id,
        "user_data": user_data,   # 👈 Pass user data to template
    }

    autopopup = request.session.pop('autopopup', False)
    
    if autopopup:
        # 2. Add the payment-related data to the context
        order_pk = request.session.pop('order_pk', None)
        razorpay_key = request.session.pop('razorpay_key', None)
        razorpay_order_id = request.session.pop('razorpay_order_id', None)

        # 3. Fetch the Order object to pass to the template
        if order_pk:
            order = Order.objects.filter(pk=order_pk).first()
        else:
            order = None

        # 4. Update the context with the retrieved data
        context.update({
            "razorpay_key": razorpay_key,
            "razorpay_order_id": razorpay_order_id,
            "order": order,
            "autopopup": autopopup,
        })

    return render(request, "checkout_page.html", context)



def get_razorpay_client():
    """
    Returns a fresh Razorpay client instance using settings credentials.
    """
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))




def generate_order_number(user):
    now = timezone.now()
    # DDMMYYYYHHMMSSmmm  (day,month,year,hour,min,sec,millisec)
    timestamp = now.strftime("%d%m%Y%H%M%S") + f"{int(now.microsecond/1000):03d}"
    return f"ORD-{user.id}-{timestamp}"





@login_required
@require_POST
@never_cache
def initiate_payment(request,cart_item_id=None):

    register_address = request.POST.get("registeraddress")

    user = request.user
    cart = Cart.objects.filter(user=user).first()

    # Handle case: cart doesn't exist
    if not cart:
        return redirect('home_page')

    # Full cart
    if cart_item_id is None:
        cart_items = Cart_Item.objects.select_related('cart','product').filter(cart=cart)
        if not cart_items:
            return redirect('home_page')
    else:
        # Single item
        cart_items = Cart_Item.objects.select_related('cart','product').filter(cart=cart, id=cart_item_id)
        if not cart_items:
            return redirect('home_page')

    total_amount = sum(item.get_total_discount_price for item in cart_items)
    delivery_charge = Decimal(DELIVERY_AMOUNT) if total_amount < Decimal(DELIVERY_CHARGE_BILLVALUE) else Decimal("0")
    final_amount = total_amount + delivery_charge              
    final_amount_paise = _to_paise_rupees_decimal(final_amount)


    order_number = generate_order_number(user)
    receipt = order_number.replace("ORD-", "")
    order = Order.objects.create(
        user=user,
        order_number=order_number,
        delivery_charge=delivery_charge,
        amount=final_amount,
        currency="INR",
        receipt=f"RCT-{receipt}",
        cart_item_ids=[ci.id for ci in cart_items],
        status="created",
    )

    if register_address:
        # 1️⃣ Create shipping address for user registered addresss
        ShippingAddress.objects.create(
            order=order,
            firstname=user.name,
            email=user.email,
            address=user.address,
            city=user.city,
            state=user.state,
            pincode=user.pincode,
            phone=user.phone
        )

    else:
        # 1️⃣ Create shipping address first
        ShippingAddress.objects.create(
            order=order,
            firstname=request.POST.get('firstname'),
            lastname=request.POST.get('lastname'),
            email=request.POST.get('email'),
            address=request.POST.get('address'),
            city=request.POST.get('city'),
            state=request.POST.get('state'),
            pincode=request.POST.get('pincode'),
            phone=request.POST.get('phone')
        )

    # First, check all items
    out_of_stock_items = []
    for ci in cart_items:
        
        if ci.product.available_stock < ci.quantity:
            # Add error message
            out_of_stock_items.append(ci.product.product_name)

    if out_of_stock_items:
            # Show error message for all out-of-stock products
        messages.error(request,f"Not enough stock for: {', '.join(out_of_stock_items)}")  
        # Redirect to cart page
        return redirect('cart_page')

    for ci in cart_items:
        # Reduce stock
        ci.product.available_stock -= ci.quantity
        ci.product.save(update_fields=["available_stock"])
        

        OrderItem.objects.create(
            order=order,
            product_id=ci.product.id,
            product_name=ci.product.product_name,
            category_name=ci.product.category.category_name,
            quantity=ci.quantity,
            unit_price=ci.product.discounted_price,
        )

    # 2) Create Razorpay order
    cart_item_ids = [item.id for item in cart_items]
    client = get_razorpay_client()
    rzp_order = client.order.create({
        "amount": final_amount_paise,
        "currency": "INR",
        "receipt": order.receipt,
        "payment_capture": "1",
        "notes": {"order_number": order_number,
                    "cart_item_ids": cart_item_ids,},
        "partial_payment": False,
    })
    order.razorpay_order_id = rzp_order["id"]
    order.save(update_fields=["razorpay_order_id"])
    

    request.session['razorpay_key'] = settings.RAZORPAY_KEY_ID
    request.session['razorpay_order_id'] = rzp_order["id"]
    request.session['autopopup'] = True
    request.session['order_pk'] = order.pk

    # 2. Redirect the user to the checkout page with a GET request
    if cart_item_id:
        return redirect('checkout_page', cart_item_id=cart_item_id)
    else:
        return redirect('checkout_page')
        
    


@login_required
@require_POST
@csrf_exempt
def verify_payment(request):
    """
    Razorpay sends POST here after payment.
    1. Verify signature
    2. Fetch payment details from Razorpay
    3. Save payment record
    4. Update order status
    5. Clear purchased cart items
    6. Redirect to payment_success page
    """

    rzp_payment_id = request.POST.get("razorpay_payment_id")
    rzp_order_id = request.POST.get("razorpay_order_id")
    rzp_signature = request.POST.get("razorpay_signature")

    if not (rzp_payment_id and rzp_order_id and rzp_signature):

        order_pk = request.session.pop('order_pk', None)

        if order_pk:
            order = Order.objects.filter(pk=order_pk, status="created").first()

            order.update(status="failed")
            order.order_payment_status = "failed"
            order.delivery_status = "failed"
            order.save(update_fields=["order_payment_status","delivery_status"])
            
            for oi in order.orderitem.all():
                
                # Restore stock
                oi.product.available_stock += oi.quantity
                oi.product.save(update_fields=["available_stock"])
            
        return redirect("payment_failed_page", order_id=order.id)
    
    client = get_razorpay_client()

    # Verify signature
    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": rzp_order_id,
            "razorpay_payment_id": rzp_payment_id,
            "razorpay_signature": rzp_signature,
        })
    except razorpay.errors.SignatureVerificationError:
        order = Order.objects.filter(razorpay_order_id=rzp_order_id, status="created").first()

        order.update(status="failed")
        order.order_payment_status = "failed"
        order.delivery_status = "failed"
        order.save(update_fields=["order_payment_status","delivery_status"])
        
        for oi in order.orderitem.all():
                
                # Restore stock
            oi.product.available_stock += oi.quantity
            oi.product.save(update_fields=["available_stock"])
        
            
        return redirect("payment_failed_page", order_id=order.id)

    # Fetch order & payment details
    order = Order.objects.filter(razorpay_order_id=rzp_order_id, status="created").first()

    payment_data = client.payment.fetch(rzp_payment_id)

    # Save payment (or update)
    Payment.objects.update_or_create(
        order=order,
        defaults={
            "razorpay_payment_id": rzp_payment_id,
            "razorpay_signature": rzp_signature,
            "method": payment_data.get("method"),
            "email": payment_data.get("email"),
            "contact": payment_data.get("contact"),
            "bank": payment_data.get("bank"),
            "wallet": payment_data.get("wallet"),
            "vpa": payment_data.get("vpa"),
            "international": payment_data.get("international", False),
            "amount": payment_data.get("amount", 0),
            "currency": payment_data.get("currency", "INR"),
            "status": payment_data.get("status"),
            "captured": payment_data.get("captured", False),
            "fee": payment_data.get("fee") or 0,
            "tax": payment_data.get("tax") or 0,
            "error_code": payment_data.get("error_code"),
            "error_description": payment_data.get("error_description"),
            "raw_response": payment_data,
        },
    )

    # Mark order as paid (captured means money received)
    order.status = "paid" if payment_data.get("status") == "captured" else "failed"
    order.save(update_fields=["status"])

    # Clear purchased cart items (respect single vs full cart)
    if order.status == "paid":
   
        order.order_payment_status = "paid"
        order.delivery_status = "confirmed"

        order.save(update_fields=["order_payment_status","delivery_status"])

        cart_item_ids = order.cart_item_ids or []
        if cart_item_ids:
            Cart_Item.objects.filter(id__in=cart_item_ids).delete()
            return redirect("payment_success_page", order_id=order.id )
            
       

    elif order.status == "failed":

        order.order_payment_status = "failed"
        order.delivery_status = "failed"
        order.save(update_fields=["order_payment_status","delivery_status"])

        for oi in order.orderitem.all():
            
            # Restore stock
            oi.product.available_stock += oi.quantity
            oi.product.save(update_fields=["available_stock"])

        return redirect("payment_failed_page", order_id=order.id)

    


@login_required
@require_POST
@csrf_exempt
def payment_cancel(request, razorpay_order_id):
    order = Order.objects.filter(razorpay_order_id=razorpay_order_id, status="created").first()

    if order:
        order.status = "cancelled"
        order.save(update_fields=["status"])
        order.order_payment_status = "failed"
        order.delivery_status = "failed"
        order.save(update_fields=["order_payment_status","delivery_status"])

        for oi in order.orderitem.all():
             # Restore stock
            oi.product.available_stock += oi.quantity
            oi.product.save(update_fields=["available_stock"])

    return JsonResponse({"ok": True})

    




def verify_signature(payload, signature):
    expected = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


    


@login_required
def payment_success_page(request,order_id):

    order=Order.objects.select_related('user').filter(pk=order_id, user = request.user).first()
    context = {
        'order':order,
    }
    return render(request, "payment_success_page.html",context)




@login_required
def payment_failed_page(request,order_id):
    order=Order.objects.select_related('user').filter(pk=order_id, user = request.user).first()
    context = {
        'order':order,
    }
    return render(request, "payment_failed_page.html",context)
      

    


@login_required
def wishlist_page(request):
    wishlist_items=Wishlist_Cart_Item.objects.select_related('wishlistcart','product').filter(wishlistcart__user=request.user)
    cart_items = Cart_Item.objects.filter(cart__user=request.user) if request.user.is_authenticated else []
    cart_dict = {item.product_id for item in cart_items}
    context = {
        'wishlist_items':wishlist_items,
        'cart_dict':cart_dict,
    }
    return render(request, 'wishlist_page.html', context)




@login_required
def add_to_wishlistcart(request, product_id):
    next_url = request.GET.get('next')

    selected_product = Product.objects.filter(id=product_id).first()
    wishlistcart, _ = Wishlist_Cart.objects.get_or_create(user=request.user)
    wishlistcart_item = Wishlist_Cart_Item.objects.create(
                wishlistcart=wishlistcart,
                product=selected_product,
            )
    wishlistcart_item.save()
    return redirect(next_url)




@login_required
def remove_from_wishlistcart(request, product_id):
    next_url = request.GET.get('next')

    selected_wishlist_item = Wishlist_Cart_Item.objects.filter(wishlistcart__user=request.user, product__id=product_id).first()
    selected_wishlist_item.delete()
    return redirect(next_url)




@login_required
def clearwishlist(request):

    wishlistcart = Wishlist_Cart.objects.filter(user=request.user).first()
    if wishlistcart:
        wishlistcart.delete()
        messages.success(request, f"'{request.user.name}' wishlist cart cleared successfully.")
        return redirect('wishlist_page')
        

@login_required
def user_profile_page(request):
    return render(request, 'user_profile_page.html')



@login_required
def user_profile_details_edit(request):
    user = request.user
    action = request.POST.get('action')

    if action == "edit-profilepicture":

        new_profile_picture = request.FILES.get('profile_picture')

        if not new_profile_picture:
            messages.error(request, "No Profile Picture is selected.")
        else:
            user.user_profile_picture = new_profile_picture
            user.save(update_fields=['user_profile_picture'])
            messages.success(request, "Profile Picture updated successfully.")

        return redirect('user_profile_page')


    elif action == "edit-name":

        new_username = request.POST.get('name')

        if user.name == new_username:
            messages.error(request, "Name is same as previous one.")
        elif len(new_username) >= 50 :
            messages.error(request, "Name should contain less than 50 letters.")
        elif not re.fullmatch(r'[A-Za-z ]+', new_username):
            messages.error(request, "Name can only contain letters and spaces.")
        elif len(re.sub(r'[^A-Za-z]', '', new_username)) < 4:
            messages.error(request, "Name must contain at least 4 letters.")
        elif not new_username.strip():
            messages.error(request, "Name cannot be empty or spaces only.")
        else:
            user.name = new_username
            user.save(update_fields=['name'])
            messages.success(request, "Name updated successfully.")

        return redirect('user_profile_page')
    

    elif action == "edit_phone":

        new_phone = request.POST.get('phone')

        if user.phone == new_phone:
            messages.error(request, "Phone number is same as previous one.")
        elif not re.fullmatch(r'\d{10}', new_phone):
            messages.error(request, "Phone number must be exactly 10 digits.")
        elif User_detail.objects.exclude(id=user.id).filter(phone=new_phone).exists():
            messages.error(request, "Phone number already taken.")
        elif not new_phone.strip():
            messages.error(request, "Phone number cannot be empty or spaces only.")
        else:
            user.phone = new_phone
            user.save(update_fields=['phone'])
            messages.success(request, "Phone Number updated successfully.")

        return redirect('user_profile_page')




    elif action == "edit_email":
            
        new_email = request.POST.get('email')

        if user.email == new_email:
            messages.error(request, "Email ID is same as previous one")
        elif not re.fullmatch(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$', new_email):
            messages.error(request, "Email ID is invalid.")
        elif User_detail.objects.exclude(id=user.id).filter(email=new_email).exists():
            messages.error(request, "Email ID already taken.")
        elif not new_email.strip():
            messages.error(request, "Email ID cannot be empty or spaces only.")
        else:
            user.email = new_email
            user.save(update_fields=['email'])
            messages.success(request, "Email ID updated successfully.")

        return redirect('user_profile_page')



    elif action == "edit_gender":
            
        new_gender = request.POST.get('gender') 

        if user.gender == new_gender:
            messages.error(request, "Gender is same as previous one") 
        else:
            user.gender = new_gender
            user.save(update_fields=['gender'])
            messages.success(request, "Gender updated successfully.")

        return redirect('user_profile_page')


    elif action == "edit_address":
            
        new_address = request.POST.get('address') 

        if user.address == new_address:
            messages.error(request, "Address is same as previous one")
        elif len(new_address) >= 200 :
            messages.error(request, "Address should contain less than 200 letters.") 
        elif not new_address.strip():
            messages.error(request, "Address cannot be empty or spaces only.")
        else:
            user.address = new_address
            user.save(update_fields=['address'])
            messages.success(request, "Address updated successfully.")

        return redirect('user_profile_page')
    

    elif action == "edit_city":

        new_city = request.POST.get('city') 
        if user.city == new_city:
            messages.error(request, "City is same as previous one")
        elif len(new_city) >= 50 :
            messages.error(request, "city should contain less than 50 letters.")
        elif not new_city.strip():
            messages.error(request, "City cannot be empty or spaces only.")
        else:
            user.city = new_city
            user.save(update_fields=['city'])
            messages.success(request, "City updated successfully.")

        return redirect('user_profile_page')
    
    
    elif action == "edit_state":

        new_state = request.POST.get('state') 
        if user.state == new_state:
            messages.error(request, "State is same as previous one")
        elif len(new_state) >= 50 :
            messages.error(request, "State should contain less than 50 letters.")
        elif not new_state.strip():
            messages.error(request, "State cannot be empty or spaces only.")
        else:
            user.state = new_state
            user.save(update_fields=['state'])
            messages.success(request, "State updated successfully.")

        return redirect('user_profile_page')
    

    elif action == "edit_pincode":

        new_pincode = request.POST.get('pincode')

        if user.pincode == new_pincode:
            messages.error(request, "Pincode is same as previous one.")
        elif not re.fullmatch(r'\d{6}', new_pincode):
            messages.error(request, "Pincode must be exactly 6 digits.")
        elif not new_pincode.strip():
            messages.error(request, "Pincode cannot be empty or spaces only.")
        else:
            user.pincode = new_pincode
            user.save(update_fields=['pincode'])
            messages.success(request, "Pincode updated successfully.")

        return redirect('user_profile_page')
    

@login_required
def order_tracking_page(request, order_id=None):
    
    order=Order.objects.select_related('user').filter(pk=order_id, user = request.user).first()

    order_items = order.orderitem.all()
    total_quantity = sum(item.quantity for item in order_items)

    context = {
        'order':order,
        'order_items':order_items,
        'total_quantity':total_quantity,
    }
    
    return render(request, "order_tracking_page.html",context)




@login_required
def order_search_page(request):
    if request.method=="GET":
        return render(request, "order_search_page.html")
    
    if request.method=="POST":

        order_number = request.POST.get('order_id')
        order=Order.objects.select_related('user').filter(order_number=order_number, user = request.user).first()

        order_items = order.orderitem.all()
        total_quantity = sum(item.quantity for item in order_items)

        context = {
            'order':order,
            'order_items':order_items,
            'order_number':order_number,
            'total_quantity':total_quantity,
        }

        return render(request, "order_search_page.html", context)
    



@never_cache
def user_login(request):
    if request.method == "GET":
        if request.user.is_authenticated:
            return redirect('home_page')
        else: 
            next_url = request.GET.get('next', '') or request.session.pop('next_url', '')
            prefill = request.session.pop('loginprefill', None)
            context = {
                            'next': next_url,
                            'prefill':prefill,
            }
            return render(request, 'user_login_page.html', context)
        
    elif request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember_me = request.POST.get("remember_me")
        next_url = request.POST.get('next')
        
        user = User_detail.objects.filter(
            phone = username if username.isdigit() else None
            ).first() if username.isdigit() else User_detail.objects.filter(email=username).first()
            
        if not user:
            request.session['next_url'] = next_url
            prefill = {
                'username': username,
                'password': "",
            }
            request.session['loginprefill'] = prefill
            messages.error(request, "Invalid Username.")
            return redirect('user_login')

        # Check password
        elif not user.check_password(password):
            request.session['next_url'] = next_url
            prefill = {
                'username': username,
                'password': password,
            }
            request.session['loginprefill'] = prefill
            messages.error(request, "Invalid Password.")
            return redirect('user_login')

        # Check if user is active
        elif not user.is_active:
            request.session['next_url'] = next_url
            prefill = {
                'username': username,
                'password': "",
            }
            request.session['loginprefill'] = prefill
            messages.error(request, "Account inactive. Contact Admin.")
            return redirect('user_login')
        
        else:
            # Log in the user
            login(request, user, 'django.contrib.auth.backends.ModelBackend')
            if remember_me == "on":
                request.session.set_expiry(None)  
            else:
                request.session.set_expiry(0)
            messages.success(request, f"Login successful. Welcome {user.name}.")
            return redirect(next_url or 'home_page')


 


@never_cache
def user_register(request):
    if request.method == "GET":
        if request.user.is_authenticated:
            return redirect('user_login')
        
        else:
            prefill = request.session.pop('signupprefill', None)
            context = {
                'prefill':prefill,
            }

            return render(request,'user_register_page.html',context)
    elif request.method == "POST":
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        valid = True

        if not name.strip():
            messages.error(request, "Name cannot be empty or spaces only.")
            valid = False
        elif len(name) >= 50 :
            messages.error(request, "Name should contain less than 50 letters.")
            valid = False
        elif not re.fullmatch(r'[A-Za-z ]+', name):
            messages.error(request, "Name can only contain letters and spaces.")
            valid = False
        elif len(re.sub(r'[^A-Za-z]', '', name)) < 4:
            messages.error(request, "Name must contain at least 4 letters.")
            valid = False

        # 2. Phone number validation
        if not re.fullmatch(r'\d{10}', phone):
            messages.error(request, "Phone number must be exactly 10 digits.")
            valid = False
        elif User_detail.objects.filter(phone=phone).exists():
            messages.error(request, "Phone number already registered.")
            valid = False

        # 3. Email validation
        if not re.fullmatch(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$', email):
            messages.error(request, "Email ID invalid")
            valid = False
        elif User_detail.objects.filter(email=email).exists():
            messages.error(request, "Email ID already registered.")
            valid = False

        # 4. Password validation
        if len(password) < 6 or len(password) > 18:
            messages.error(request, "Password must be 6-18 characters.")
            valid = False
        elif not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            messages.error(request, "Password must include at least one special character.")
            valid = False
        elif not re.search(r'[A-Z]', password):
            messages.error(request, "Password must include at least one uppercase letter.")
            valid = False
        elif not re.search(r'[a-z]', password):
            messages.error(request, "Password must include at least one lowercase letter.")
            valid = False
        elif not re.search(r'\d', password):
            messages.error(request, "Password must include at least 1 number.")
            valid = False

        # 5. Confirm password match
        if password != confirm_password:
            messages.error(request, "Confirm Passwords not match with password.")
            valid = False

        if valid:
            # Create user
            User_detail.objects.create_user(
                phone=phone,
                email=email,
                password=password,
                name=name,
            )
            messages.success(request, "User Registrated successful.")
            return redirect('user_login')
        else:
            prefill = {
                'name': name,
                'phone': phone,
                'email': email,
                "password": password,
                "confirmpassword" : confirm_password
            }
            request.session['signupprefill'] = prefill
            return redirect('user_register')
        

class CustomPasswordResetView(PasswordResetView):

    form_class = RateLimitedPasswordResetForm
    template_name = 'registration/password_reset_form.html'
    email_template_name = 'registration/password_reset_email.html'
    subject_template_name = 'registration/password_reset_subject.txt'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request  # Pass request to form for IP access
        return kwargs



@login_required
def user_logout(request):
    logout(request)  
    messages.success(request, "Signed out successfully. Bye...")
    return redirect('home_page')