# inventory/models.py
from django.db import models
from django.contrib.auth.models import User
import uuid
import qrcode
from django.core.files import File
from io import BytesIO

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    def __str__(self):
        return self.name

class Subcategory(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
    class Meta:
        unique_together = ['name', 'category']
    def __str__(self):
        return f"{self.category.name} - {self.name}"

class Warehouse(models.Model):
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=200)
    unique_id = models.CharField(max_length=50, unique=True, editable=False)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    subcategory = models.ForeignKey(Subcategory, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=0)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    photo = models.ImageField(upload_to='products/photos/', blank=True, null=True)  # Для изображения товара
    qr_code = models.ImageField(upload_to='products/qr_codes/', blank=True, null=True)  # Для QR-кода
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        if not self.unique_id:
            self.unique_id = str(uuid.uuid4())[:50]
        # Генерация и сохранение QR-кода
        qr = qrcode.QRCode()
        qr.add_data(self.unique_id)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        self.qr_code.save(f"qr_{self.unique_id}.png", File(buffer), save=False)
        super().save(*args, **kwargs)
        if self.quantity < 5:
            if hasattr(self, 'request'):
                self.request.session['low_stock'] = f"Товар {self.name} заканчивается (осталось {self.quantity})"

    def __str__(self):
        return self.name

class Sale(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    date = models.DateTimeField(auto_now_add=True)
    base_price_total = models.DecimalField(max_digits=10, decimal_places=2)
    actual_price_total = models.DecimalField(max_digits=10, decimal_places=2)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

class UserSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    hide_cost_price = models.BooleanField(default=False)

class LogEntry(models.Model):
    ACTION_TYPES = (
        ('LOGIN', 'Вход'),
        ('LOGOUT', 'Выход'),
        ('REGISTER', 'Регистрация'),
        ('ADD', 'Добавление'),
        ('DELETE', 'Удаление'),
        ('UPDATE', 'Обновление'),
        ('SALE', 'Продажа'),
        ('BLOCK', 'Блокировка'),
        ('UNBLOCK', 'Разблокировка'),
    )

    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='inventory_log_entries')
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    message = models.TextField()

    def __str__(self):
        return f"{self.timestamp} - {self.get_action_type_display()} - {self.message}"