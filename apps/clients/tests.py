from django.test import TestCase
from apps.clients.models import Client, UserClient

class ClientTest(TestCase):
    def test_client_creation(self):
        client = Client.objects.create(
            email="test@test.com",
            shop="test",
            first_name="test",
            last_name="test"
        )
        self.assertEqual(client.email, "test@test.com")
        self.assertEqual(client.shop, "test")
        self.assertEqual(client.first_name, "test")
        self.assertEqual(client.last_name, "test")

    def test_user_client_creation(self):
        client = Client.objects.create(
            email="test@test.com",
            shop="test",
            first_name="test",
            last_name="test"
        )
        user_client = UserClient.objects.create(
            email="test@test.com",
            from_client=client
        )
        self.assertEqual(user_client.email, "test@test.com")
        self.assertEqual(user_client.from_client, client)