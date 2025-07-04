# inventory/tests.py
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.db import connection
import os
from inventory.models import Product, Warehouse, Sale, SaleItem, Category, Subcategory, LogEntry, Cart, UserSettings

class AuthTestCase(TestCase):
    def setUp(self):
        self.register_url = reverse('register')
        self.login_url = reverse('login')

    def tearDown(self):
        User.objects.all().delete()

    def test_register(self):
        response = self.client.post(self.register_url, {
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': 'Test',
            'password1': 'testpassword123',
            'password2': 'testpassword123',
        })
        self.assertRedirects(response, self.login_url)
        self.assertTrue(User.objects.filter(username='testuser').exists())
        user = User.objects.get(username='testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.first_name, 'Test')
        self.assertTrue(user.check_password('testpassword123'))

    def test_login(self):
        User.objects.create_user(username='testuser', password='testpassword123')
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'testpassword123',
        })
        self.assertRedirects(response, reverse('products'))
        self.assertTrue(self.client.session.get('_auth_user_id'))

    def test_login_invalid_credentials(self):
        User.objects.create_user(username='testuser', password='testpassword123')
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'wrongpassword',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Неверный логин или пароль')
        self.assertFalse(self.client.session.get('_auth_user_id'))

class ProductTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        # Create UserSettings for the user
        UserSettings.objects.create(user=self.user)
        self.category = Category.objects.create(name='Test Category')
        self.subcategory = Subcategory.objects.create(name='Test Subcategory', category=self.category)
        self.warehouse = Warehouse.objects.create(name='Test Warehouse', owner=self.user)
        self.product = Product.objects.create(
            name='Test Product',
            owner=self.user,
            quantity=10,
            selling_price=100,
            category=self.category,
            subcategory=self.subcategory,
            warehouse=self.warehouse
        )

    def tearDown(self):
        Product.objects.all().delete()
        Warehouse.objects.all().delete()
        Subcategory.objects.all().delete()
        Category.objects.all().delete()
        UserSettings.objects.all().delete()
        User.objects.all().delete()

    def test_product_creation(self):
        self.assertEqual(self.product.name, 'Test Product')
        self.assertEqual(self.product.quantity, 10)
        self.assertEqual(self.product.selling_price, 100)
        self.assertEqual(self.product.category.name, 'Test Category')
        self.assertEqual(self.product.subcategory.name, 'Test Subcategory')
        self.assertEqual(self.product.warehouse.name, 'Test Warehouse')
        self.assertTrue(self.product.unique_id)
        self.assertTrue(self.product.qr_code)  # Проверяем поле qr_code
        self.assertTrue(self.product.qr_code.name.startswith('products/qr_codes/qr_'))  # Проверяем путь QR-кода

    def test_product_qr_code_generation(self):
        # Проверяем только имя файла, так как файл может не существовать в тестовой среде
        self.assertTrue(self.product.qr_code.name.endswith('.png'))

class SaleTestCase(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword123')
        # Create UserSettings for the user
        UserSettings.objects.create(user=self.user)
        self.category = Category.objects.create(name='Test Category')
        self.subcategory = Subcategory.objects.create(name='Test Subcategory', category=self.category)
        self.warehouse = Warehouse.objects.create(name='Test Warehouse', owner=self.user)
        self.product = Product.objects.create(
            name='Test Product',
            owner=self.user,
            quantity=10,
            selling_price=100,
            category=self.category,
            subcategory=self.subcategory,
            warehouse=self.warehouse
        )

    def tearDown(self):
        Sale.objects.all().delete()
        Product.objects.all().delete()
        Warehouse.objects.all().delete()
        Subcategory.objects.all().delete()
        Category.objects.all().delete()
        UserSettings.objects.all().delete()
        User.objects.all().delete()
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='inventory_sale';")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='inventory_product';")

    def test_sale(self):
        self.client.login(username='testuser', password='testpassword123')

        # Создаем корзину
        response = self.client.post(reverse('cart_create'))
        self.assertEqual(response.status_code, 302)
        cart = Cart.objects.filter(owner=self.user).first()
        self.assertIsNotNone(cart)

        # Добавляем товар в корзину
        response = self.client.post(reverse('cart_add_item', args=[cart.id]), {
            'product': self.product.id,
            'quantity': 2,
            'actual_price': 90,
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(cart.items.count(), 1)

        # Подтверждаем корзину для создания продажи
        response = self.client.post(reverse('cart_confirm', args=[cart.id]))
        self.assertRedirects(response, reverse('sales_list'))

        # Проверяем продажу
        sale = Sale.objects.filter(owner=self.user).first()
        self.assertIsNotNone(sale)
        sale_item = sale.items.first()
        self.assertEqual(sale_item.product, self.product)
        self.assertEqual(sale_item.quantity, 2)
        self.assertEqual(sale_item.actual_price_total, 180)  # 90 * 2
        self.assertEqual(sale_item.base_price_total, 200)   # 100 * 2

        # Проверяем обновление количества товара
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 8)

    def test_sale_insufficient_quantity(self):
        self.client.login(username='testuser', password='testpassword123')

        # Создаем корзину
        response = self.client.post(reverse('cart_create'))
        self.assertEqual(response.status_code, 302)
        cart = Cart.objects.filter(owner=self.user).first()
        self.assertIsNotNone(cart)

        # Пытаемся добавить товара больше, чем есть в наличии
        response = self.client.post(reverse('cart_add_item', args=[cart.id]), {
            'product': self.product.id,
            'quantity': 15,  # Больше, чем доступно (10)
            'actual_price': 90,
        })
        self.assertEqual(response.status_code, 200)  # Остаемся на той же странице из-за ошибки
        self.assertContains(response, 'Недостаточно товара на складе')
        self.assertEqual(cart.items.count(), 0)  # Товар не добавлен из-за недостаточного количества

        # Проверяем, что продажа не создана
        self.assertFalse(Sale.objects.filter(owner=self.user).exists())

        # Проверяем, что количество товара не изменилось
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 10)

class IsolationTestCase(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='testpassword123')
        self.user2 = User.objects.create_user(username='user2', password='testpassword123')
        # Create UserSettings for both users
        UserSettings.objects.create(user=self.user1)
        UserSettings.objects.create(user=self.user2)
        self.category = Category.objects.create(name='Test Category')
        self.subcategory = Subcategory.objects.create(name='Test Subcategory', category=self.category)
        self.warehouse1 = Warehouse.objects.create(name='Warehouse1', owner=self.user1)
        self.warehouse2 = Warehouse.objects.create(name='Warehouse2', owner=self.user2)
        self.product1 = Product.objects.create(
            name='Product1',
            owner=self.user1,
            quantity=10,
            selling_price=100,
            category=self.category,
            subcategory=self.subcategory,
            warehouse=self.warehouse1
        )
        self.product2 = Product.objects.create(
            name='Product2',
            owner=self.user2,
            quantity=20,
            selling_price=200,
            category=self.category,
            subcategory=self.subcategory,
            warehouse=self.warehouse2
        )

    def tearDown(self):
        Product.objects.all().delete()
        Warehouse.objects.all().delete()
        Subcategory.objects.all().delete()
        Category.objects.all().delete()
        UserSettings.objects.all().delete()
        User.objects.all().delete()

    def test_isolation(self):
        self.client.login(username='user1', password='testpassword123')
        response = self.client.get(reverse('products'))
        self.assertContains(response, 'Product1')
        self.assertNotContains(response, 'Product2')
        self.assertEqual(Product.objects.filter(owner=self.user1).count(), 1)
        self.assertEqual(Product.objects.filter(owner=self.user2).count(), 1)

    def test_isolation_user2(self):
        self.client.login(username='user2', password='testpassword123')
        response = self.client.get(reverse('products'))
        self.assertContains(response, 'Product2')
        self.assertNotContains(response, 'Product1')

class NotificationTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword123')
        # Create UserSettings for the user
        UserSettings.objects.create(user=self.user)
        self.category = Category.objects.create(name='Test Category')
        self.subcategory = Subcategory.objects.create(name='Test Subcategory', category=self.category)
        self.warehouse = Warehouse.objects.create(name='Test Warehouse', owner=self.user)
        self.product = Product.objects.create(
            name='Test Product',
            owner=self.user,
            quantity=3,
            selling_price=100,
            category=self.category,
            subcategory=self.subcategory,
            warehouse=self.warehouse
        )

    def tearDown(self):
        Product.objects.all().delete()
        Warehouse.objects.all().delete()
        Subcategory.objects.all().delete()
        Category.objects.all().delete()
        UserSettings.objects.all().delete()
        User.objects.all().delete()

    def test_low_stock_notification(self):
        self.client.login(username='testuser', password='testpassword123')
        # Вручную устанавливаем значение в сессии
        session = self.client.session
        session['low_stock'] = 'Товар Test Product заканчивается (осталось 3)'
        session.save()

        response = self.client.get(reverse('products'))
        self.assertContains(response, 'Осталось мало товара!')
        self.assertContains(response, 'Товар Test Product заканчивается (осталось 3)')
        self.assertIsNone(self.client.session.get('low_stock'))

    def test_no_notification_high_stock(self):
        self.product.quantity = 10
        self.product.save()
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(reverse('products'))
        self.assertNotContains(response, 'Осталось мало товара!')
        self.assertIsNone(self.client.session.get('low_stock'))

class AdminTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username='admin', password='adminpassword123')
        self.user = User.objects.create_user(username='testuser', password='testpassword123')
        # Create UserSettings for both users
        UserSettings.objects.create(user=self.admin)
        UserSettings.objects.create(user=self.user)
        self.admin_panel_url = reverse('admin_panel')

    def tearDown(self):
        UserSettings.objects.all().delete()
        User.objects.all().delete()

    def test_block_user(self):
        self.client.login(username='admin', password='adminpassword123')
        response = self.client.post(self.admin_panel_url, {
            'user_id': self.user.id,
            'action': 'block',
        })
        self.assertRedirects(response, self.admin_panel_url)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    def test_delete_user(self):
        self.client.login(username='admin', password='adminpassword123')
        response = self.client.post(self.admin_panel_url, {
            'user_id': self.user.id,
            'action': 'delete',
        })
        self.assertRedirects(response, self.admin_panel_url)
        self.assertFalse(User.objects.filter(id=self.user.id).exists())

    def test_non_admin_access(self):
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(self.admin_panel_url)
        self.assertRedirects(response, '/login/?next=/admin-panel/')
        self.assertEqual(response.status_code, 302)

class CategoryTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username='admin', password='adminpassword123')
        self.user = User.objects.create_user(username='testuser', password='testpassword123')
        # Create UserSettings for both users
        UserSettings.objects.create(user=self.admin)
        UserSettings.objects.create(user=self.user)
        self.category_url = reverse('category_manage')

    def tearDown(self):
        Subcategory.objects.all().delete()
        Category.objects.all().delete()
        UserSettings.objects.all().delete()
        User.objects.all().delete()

    def test_create_category(self):
        self.client.login(username='admin', password='adminpassword123')
        response = self.client.post(self.category_url, {
            'name': 'New Category',
            'add_category': '1',  # Добавляем ключ для обработки формы
        })
        self.assertRedirects(response, self.category_url)
        self.assertTrue(Category.objects.filter(name='New Category').exists())

    def test_create_subcategory(self):
        category = Category.objects.create(name='Test Category')
        self.client.login(username='admin', password='adminpassword123')
        response = self.client.post(self.category_url, {
            'name': 'New Subcategory',
            'category': category.id,
            'add_subcategory': '1',  # Добавляем ключ для обработки формы
        })
        self.assertRedirects(response, self.category_url)
        self.assertTrue(Subcategory.objects.filter(name='New Subcategory', category=category).exists())

    def test_delete_category(self):
        category = Category.objects.create(name='Test Category')
        self.client.login(username='admin', password='adminpassword123')
        response = self.client.post(reverse('category_delete', args=[category.id]))
        self.assertRedirects(response, self.category_url)
        self.assertFalse(Category.objects.filter(id=category.id).exists())

    def test_non_admin_access(self):
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(self.category_url)
        self.assertRedirects(response, '/login/?next=/categories/')
        self.assertEqual(response.status_code, 302)

class WarehouseTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword123')
        # Create UserSettings for the user
        UserSettings.objects.create(user=self.user)
        self.warehouse_url = reverse('warehouses')

    def tearDown(self):
        Warehouse.objects.all().delete()
        UserSettings.objects.all().delete()
        User.objects.all().delete()

    def test_create_warehouse(self):
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.post(self.warehouse_url, {
            'name': 'New Warehouse',
        })
        self.assertRedirects(response, self.warehouse_url)
        self.assertTrue(Warehouse.objects.filter(name='New Warehouse', owner=self.user).exists())

    def test_delete_warehouse(self):
        warehouse = Warehouse.objects.create(name='Test Warehouse', owner=self.user)
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.post(self.warehouse_url, {
            'warehouse_id': warehouse.id,
            'action': 'delete',
        })
        self.assertRedirects(response, self.warehouse_url)
        self.assertFalse(Warehouse.objects.filter(id=warehouse.id).exists())

class LoggingTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword123')
        self.admin = User.objects.create_superuser(username='admin', password='adminpassword123')
        # Create UserSettings for both users
        UserSettings.objects.create(user=self.user)
        UserSettings.objects.create(user=self.admin)

    def tearDown(self):
        LogEntry.objects.all().delete()
        UserSettings.objects.all().delete()
        User.objects.all().delete()

    def test_logging_user_registration(self):
        self.client.post(reverse('register'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'first_name': 'New',
            'password1': 'newpassword123',
            'password2': 'newpassword123',
        })
        log_entry = LogEntry.objects.get(action_type='REGISTER')
        self.assertEqual(log_entry.message, 'Новый пользователь newuser зарегистрирован')

    def test_logging_category_creation(self):
        self.client.login(username='admin', password='adminpassword123')
        self.client.post(reverse('category_manage'), {
            'name': 'New Category',
            'add_category': '1',
        })
        log_entry = LogEntry.objects.get(action_type='ADD')
        self.assertEqual(log_entry.message, 'Категория "New Category" добавлена администратором admin')

class ScanAndSaleTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        # Create UserSettings for the user
        UserSettings.objects.create(user=self.user)
        self.category = Category.objects.create(name='Процессоры')
        self.subcategory = Subcategory.objects.create(name='Intel', category=self.category)
        self.warehouse = Warehouse.objects.create(name='Склад 1', owner=self.user)
        self.product = Product.objects.create(
            name='Core i9',
            category=self.category,
            subcategory=self.subcategory,
            quantity=10,
            selling_price=500,
            warehouse=self.warehouse,
            owner=self.user
        )
        self.client.login(username='testuser', password='testpass')

    def test_scan_product(self):
        response = self.client.get(reverse('scan_product'), {'code': self.product.unique_id})
        self.assertEqual(response.status_code, 302)  # Ожидаем редирект на cart_add_item
        cart = Cart.objects.filter(owner=self.user).first()
        self.assertIsNotNone(cart)
        self.assertRedirects(response, reverse('cart_add_item', args=[cart.id]))

    def test_sale_with_custom_price(self):
        # Создаем корзину
        response = self.client.post(reverse('cart_create'))
        self.assertEqual(response.status_code, 302)
        cart = Cart.objects.filter(owner=self.user).first()
        self.assertIsNotNone(cart)

        # Добавляем товар в корзину с кастомной ценой
        response = self.client.post(reverse('cart_add_item', args=[cart.id]), {
            'product': self.product.id,
            'quantity': 2,
            'actual_price': 400,
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(cart.items.count(), 1)
        cart_item = cart.items.first()
        self.assertEqual(cart_item.actual_price_total, 800)  # 400 * 2

        # Подтверждаем корзину для создания продажи
        response = self.client.post(reverse('cart_confirm', args=[cart.id]))
        self.assertRedirects(response, reverse('sales_list'))

        # Проверяем продажу
        sale = Sale.objects.filter(owner=self.user).first()
        self.assertIsNotNone(sale)
        sale_item = sale.items.first()
        self.assertEqual(sale_item.actual_price_total, 800)  # 400 * 2
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 8)  # 10 - 2

class StatsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        # Create UserSettings for the user
        UserSettings.objects.create(user=self.user)
        self.category = Category.objects.create(name='Test Category')
        self.subcategory = Subcategory.objects.create(name='Test Subcategory', category=self.category)
        self.warehouse = Warehouse.objects.create(name='Test Warehouse', owner=self.user)
        self.product = Product.objects.create(
            name='Test Product',
            category=self.category,
            subcategory=self.subcategory,
            quantity=10,
            cost_price=50,
            selling_price=100,
            warehouse=self.warehouse,
            owner=self.user
        )
        self.sale = Sale.objects.create(owner=self.user)
        SaleItem.objects.create(
            sale=self.sale,
            product=self.product,
            quantity=2,
            base_price_total=200,
            actual_price_total=200
        )
        self.client.login(username='testuser', password='testpass')

    def test_stats(self):
        response = self.client.get(reverse('stats'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_revenue'], 200)
        self.assertEqual(response.context['total_sales_count'], 1)

    def tearDown(self):
        Sale.objects.all().delete()
        Product.objects.all().delete()
        Warehouse.objects.all().delete()
        Subcategory.objects.all().delete()
        Category.objects.all().delete()
        UserSettings.objects.all().delete()
        User.objects.all().delete()