from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal, ROUND_CEILING
from datetime import timedelta
from django.utils import timezone
from django.utils.html import format_html
from django.templatetags.static import static



# Create your models here.
class CustomUserManager(BaseUserManager):
    def create_user(self, name, phone, email, password, **extra_fields):
        if not name:
            raise ValueError('Name is required')
        elif not phone:
            raise ValueError('Phone number is required')
        elif not email:
            raise ValueError('Email is required')
        elif not password:
            raise ValueError('Password is required')
        if email:
            email = self.normalize_email(email)
        user = self.model(name=name, phone=phone, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, name, phone, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(name, phone, email, password, **extra_fields)
    


def user_image_upload_path(instance, filename):
    from django.utils.text import slugify
    name = slugify(instance.name)
    id = instance.pk
    return f'User_images/{name}_ID_{id}/{filename}'




class User_detail(AbstractBaseUser, PermissionsMixin):

    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
    ]

    user_profile_picture = models.ImageField( null=True, blank=True, upload_to=user_image_upload_path,default="defaults/user_image_default.png")
    name = models.CharField(max_length=50,null=False, blank=False)
    phone = models.CharField(max_length=10, unique=True, null=True, blank=True)
    email = models.EmailField(unique=True, null=False, blank=False)
    gender = models.CharField(max_length=6, choices=GENDER_CHOICES, null=True, blank=True)
    address = models.CharField(max_length=200, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    pincode = models.IntegerField(null=True, blank=True)

    # Permissions / status flags
    is_active = models.BooleanField(null=True, blank=True, default=True)
    is_staff = models.BooleanField(null=True, blank=True, default=False)
    is_superuser = models.BooleanField(null=True, blank=True, default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name', 'phone']

    def __str__(self):
        return self.email or self.phone
    
    @property
    def user_id(self):
        if self.id:
            return f"USER{self.pk:03d}"
        
    @property
    def profile_picture_url(self):
        if self.user_profile_picture and self.user_profile_picture.name:
            return self.user_profile_picture.url
        return static('images/user_image_default.png')
        


class Category(models.Model):
    COLOR_CHOICES = [
        ('pink', 'Pink'),
        ('blue', 'Blue'),
        ('green', 'Green'),
        ('orange', 'Orange'),
        ('light red', 'Light red'),
        ('violet', 'Violet'),
    ]
    category_name = models.CharField(max_length=50,null=False, blank=False,unique=True)
    category_image = models.ImageField(upload_to='Categories_images/',null=False, blank=False)
    category_image_altername = models.CharField(max_length=50, null=False, blank=False)
    category_background_color = models.CharField(max_length=30,choices=COLOR_CHOICES,null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.category_name
    
    


def product_image_upload_path(instance, filename):
    from django.utils.text import slugify
    product_name = slugify(instance.product_name)
    return f'Products_images/{product_name}/{filename}'



 
class Product(models.Model):
    FEATURED_CHOICES = [
        ('Discount', 'Discount'),
        ('New', 'New'),
        ('Bestseller', 'Bestseller'),
    ]
    category = models.ForeignKey(Category, on_delete=models.CASCADE,related_name="product")
    product_name = models.CharField(max_length=500,null=False, blank=False,unique=True)
    product_main_image = models.ImageField(upload_to=product_image_upload_path, null=False, blank=False)
    product_image1 = models.ImageField(upload_to=product_image_upload_path, null=True, blank=True)
    product_image2 = models.ImageField(upload_to=product_image_upload_path, null=True, blank=True)
    product_image3 = models.ImageField(upload_to=product_image_upload_path, null=True, blank=True)
    product_image4 = models.ImageField(upload_to=product_image_upload_path, null=True, blank=True)
    product_image_altername = models.CharField(max_length=40, null=False, blank=False)
    product_short_desc = models.CharField(max_length=150,null=False, blank=False)
    product_desc = models.CharField(max_length=1500,null=False, blank=False)
    product_price = models.DecimalField(null=False, blank=False,decimal_places=2,max_digits=10,validators=[MinValueValidator(0)])
    available_stock = models.PositiveIntegerField(blank=False, null=False,help_text="If no stock while adding enter value as 0.")
    discount = models.DecimalField(null=True, blank=True, max_digits=5, decimal_places=2, 
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Enter discount between 0.00 and 100.00"
    )
    featured_option = models.CharField(max_length=10, choices=FEATURED_CHOICES, null=True, blank=True)
    rating = models.IntegerField(
        null=True, blank=True,default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Leave empty when adding products. It will auto-calculate."
    )
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"{self.product_name}"
    
    @property
    def discounted_price(self):
        """Calculate final price after discount (always round UP to 2 decimals)"""
        if self.discount and self.discount > 0:
            price = Decimal(str(self.product_price))
            discount = Decimal(str(self.discount)) / Decimal("100")
            final_price = price - (price * discount)
            return final_price.quantize(Decimal("0.01"), rounding=ROUND_CEILING)
        return Decimal(str(self.product_price)).quantize(Decimal("0.01"), rounding=ROUND_CEILING)
    


class Review(models.Model):
    RATING_CHOICES = [(i, i) for i in range(1, 6)]
    RATING_LABELS = {
        5: 'Very Good',
        4: 'Good',
        3: 'OK',
        2: 'Bad',
        1: 'Very Bad',
    }
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='review')
    user = models.ForeignKey(User_detail, on_delete=models.CASCADE,related_name='review')
    rating = models.IntegerField(choices=RATING_CHOICES)
    rating_label = models.CharField(max_length=10)
    comment = models.CharField(max_length=500, null=False, blank=False)
    disable = models.BooleanField(default=False)
    posted_on = models.DateTimeField(auto_now=True)  

    def __str__(self): 
        return f"{self.product} - {self.user} - {self.rating}"

    class Meta:
        unique_together = ('product', 'user')  

    def save(self, *args, **kwargs):
        self.rating_label = self.RATING_LABELS.get(self.rating, '')
        super().save(*args, **kwargs)
        
    
        

class Wishlist_Cart(models.Model):
    user = models.ForeignKey(User_detail, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Wishlist_Cart ({self.user.name})"
    



class Wishlist_Cart_Item(models.Model):
    wishlistcart = models.ForeignKey(Wishlist_Cart, on_delete=models.CASCADE, related_name="wishlistcartitem")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="wishlistcartitem")

    def __str__(self):
        return self.product.product_name
    

    

class Cart(models.Model):
    user = models.ForeignKey(User_detail, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart ({self.user.name})"
    



class Cart_Item(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="cartitem")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="cartitem")
    quantity = models.PositiveIntegerField(blank=False, null=False, default=1)

    def __str__(self):
        return f"{self.product.product_name} x {self.quantity}"

    @property
    def get_total_price(self):
        return self.quantity * self.product.product_price
    
    @property
    def get_total_discount_price(self):
        discount_amount = (self.product.discount or 0) / 100 * self.product.product_price
        return self.quantity * (self.product.product_price - discount_amount)
    


class Order(models.Model):
    STATUS_CHOICES = [
        ("created","Created"),
        ("paid","Paid"),
        ("cancelled", "Cancelled"),
        ("failed","Failed")
    ]

    DELIVERY_STATUS_CHOICES=[
        ("not confirmed","Not confirmed"),
        ("confirmed","Confirmed"),
        ("shipped","Shipped"),
        ("out for delivery","Out for Delivery"),
        ("delivered","Delivered"),
        ("failed","Failed")
    ]

    ORDER_PAYMENT_STATUS = [
        ("pending","Pending"),
        ("paid","Paid"),
        ("failed","Failed")
    ]

    user = models.ForeignKey(User_detail, null=True, blank=True, on_delete=models.SET_NULL)
    order_number = models.CharField(max_length=100, unique=True, null=True, blank=True)
    razorpay_order_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    cart_item_ids = models.JSONField(null=True, blank=True)  # Django >=3.1
    delivery_charge = models.DecimalField(decimal_places=2,max_digits=10)
    amount = models.DecimalField(decimal_places=2,max_digits=10,help_text="Including GST and shipping")
    currency = models.CharField(max_length=10, default="INR")
    receipt = models.CharField(max_length=64, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="created")
    delivery_status = models.CharField(max_length=20, choices=DELIVERY_STATUS_CHOICES,default="not confirmed")
    delivery_date = models.DateTimeField(null=True, blank=True)
    shipped_date = models.DateTimeField(null=True, blank=True)
    out_for_delivery_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    order_payment_status=models.CharField(max_length=20, choices=ORDER_PAYMENT_STATUS, default="pending")

    def __str__(self): 
        return f"{self.order_number}"
    
    @property
    def estimated_delivery_date(self):
        if self.updated_at:
            return self.updated_at + timedelta(days=3)
        return None
    
    def save(self, *args, **kwargs):
        # if status changes to delivered, set delivery_date
        if self.delivery_status == "delivered" and not self.delivery_date:
            self.delivery_date = timezone.now()

        if self.delivery_status == "shipped" and not self.shipped_date:
            self.shipped_date = timezone.now()    

        if self.delivery_status == "out for delivery" and not self.out_for_delivery_date:
            self.out_for_delivery_date = timezone.now() 

        super().save(*args, **kwargs)


    def list_products(self):
        items = self.orderitem.all()
        if not items:
            return "No products"

        product_list = []
        for item in items:
            line = f"{item.product_name} (x{item.quantity})"
            product_list.append(line)

        return format_html("<br>".join(product_list))

    list_products.short_description = "Products"
    


class ShippingAddress(models.Model):
    order = models.OneToOneField(Order, related_name="shippingaddress", on_delete=models.CASCADE,null=False,blank=False)
    firstname = models.CharField(max_length=50, null=False, blank=False)
    lastname = models.CharField(max_length=50, null=True, blank=True)
    email = models.EmailField(null=False, blank=False)
    phone = models.CharField(max_length=10, null=False, blank=False)
    address = models.CharField(max_length=200, null=False, blank=False)
    city = models.CharField(max_length=100, null=False, blank=False)
    state = models.CharField(max_length=100, null=False, blank=False)
    pincode = models.CharField(max_length=6, null=False, blank=False)
    

    def __str__(self):
        return f"{self.order} - {self.firstname} - {self.city}"

    
    





class OrderItem(models.Model):
    
    
    order = models.ForeignKey(Order, related_name="orderitem", on_delete=models.CASCADE)
    product = models.ForeignKey("Product", on_delete=models.SET_NULL,null=True, blank=True)   
    product_name = models.CharField(max_length=255, null=False)
    category_name = models.CharField(max_length=255, null=False)              
    quantity = models.PositiveIntegerField(null=False)
    unit_price = models.DecimalField(decimal_places=2,max_digits=10,null=False)
    
    

    def __str__(self): 
        return f"{self.product_name} x {self.quantity}"
    
    @property
    def total_price(self):
        if self.product and self.product.product_price:
            return self.product.product_price * self.quantity
        return 0
    
    @property
    def total_discount_price(self):
        if self.unit_price and self.quantity:
            return self.unit_price * self.quantity
        return 0
    
    


    




class Payment(models.Model):
    order = models.OneToOneField(Order, related_name="payment", on_delete=models.CASCADE)
    razorpay_payment_id = models.CharField(max_length=100, unique=True)
    razorpay_signature = models.CharField(max_length=256)
    method = models.CharField(max_length=30, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    contact = models.CharField(max_length=20, null=True, blank=True)
    bank = models.CharField(max_length=50, null=True, blank=True)
    wallet = models.CharField(max_length=50, null=True, blank=True)
    vpa = models.CharField(max_length=100, null=True, blank=True)
    international = models.BooleanField(default=False)
    amount = models.PositiveIntegerField(default=0,help_text="Amount is in paise")
    currency = models.CharField(max_length=10, default="INR")
    status = models.CharField(max_length=30, null=True, blank=True)
    captured = models.BooleanField(default=False)
    fee = models.PositiveIntegerField(default=0,help_text="Amount is in paise")
    tax = models.PositiveIntegerField(default=0,help_text="Amount is in paise")
    error_code = models.CharField(max_length=100, null=True, blank=True)
    error_description = models.TextField(null=True, blank=True)
    raw_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self): 
        return self.razorpay_payment_id
    


class Contact_Us_Message(models.Model):
    name = models.CharField(max_length=100, blank=False, null=False)
    email = models.EmailField(null=False, blank=False)
    message = models.CharField(max_length=1500, blank=False, null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    viewed = models.BooleanField(default=False) 
    finished = models.BooleanField(default=False) 
    pending = models.BooleanField(default=False)


    def __str__(self):
        return f"{self.name} - {self.email} - {self.message} "