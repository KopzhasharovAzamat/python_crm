from django.test import TestCase
from django.contrib.auth.models import User
from .models import Product, Warehouse, Sale, Category

class ProductTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='test', password='test')
        self.category = Category.objects.create(name='Test Category')
        self.warehouse = Warehouse.objects.create(name='Test Warehouse', owner=self.user)
        self.product = Product.objects.create(
            name='Test Product', owner=self.user, quantity=10, selling_price=100,
            category=self.category, warehouse=self.warehouse
        )

    def test_product_creation(self):
        self.assertEqual(self.product.name, 'Test Product')