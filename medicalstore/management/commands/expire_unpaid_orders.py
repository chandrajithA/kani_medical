from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from medicalstore.models import Order  # adjust import

class Command(BaseCommand):
    help = "Expire unpaid orders and restore stock"

    def handle(self, *args, **kwargs):
        expiry_time = timezone.now() - timedelta(minutes=1)
        orders = Order.objects.filter(
            status="created",
            order_payment_status="pending",
            created_at__lt=expiry_time
        )

        if not orders.exists():
            self.stdout.write(self.style.SUCCESS("No unpaid orders to expire."))
            return

        for order in orders:
            for item in order.orderitem.all():  # assuming Order has related OrderItems
                item.product.available_stock += item.quantity
                item.product.save()

            order.order_payment_status = "failed"
            order.status = "failed"
            order.delivery_status = "failed"
            order.save()

            self.stdout.write(
                self.style.WARNING(f"Order {order.id} expired, stock restored.")
            )
