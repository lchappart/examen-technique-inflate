from django.test import TestCase
from apps.orders.models import Order
from apps.clients.models import Client

class OrderTest(TestCase):
    def test_order_creation(self):
        order = Order.objects.create(
            order_id="1234567890",
            from_client=Client.objects.create(
                email="test@test.com",
                shop="test",
                first_name="test",
                last_name="test"
            )
        )
        self.assertEqual(order.order_id, "1234567890")
