# inventory/models.py
from django.db import models
from django.contrib.auth.models import User
import uuid
import qrcode
from django.core.files import File
from io import BytesIO
from django.utils import timezone

################
### CATEGORY ###
################

class Category(models.Model):
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, default=1)

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        constraints = [
            models.UniqueConstraint(fields=['name', 'owner'], name='unique_category_per_owner')
        ]

    def __str__(self):
        return self.name

###################
### SUBCATEGORY ###
###################

class Subcategory(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, default=1)

    class Meta:
        verbose_name = "Подкатегория"
        verbose_name_plural = "Подкатегории"
        constraints = [
            models.UniqueConstraint(fields=['name', 'category', 'owner'], name='unique_subcategory_per_category_owner')
        ]

    def __str__(self):
        return f"{self.name} ({self.category.name})"

#################
### WAREHOUSE ###
#################

class Warehouse(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название")
    owner = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Владелец")

    def __str__(self):
        return self.name

################
### PRODUCTS ###
################

class Product(models.Model):
    name = models.CharField(max_length=200, verbose_name="Название")
    unique_id = models.CharField(max_length=50, unique=True, editable=False, verbose_name="Уникальный идентификатор")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, verbose_name="Категория")
    subcategory = models.ForeignKey(Subcategory, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Подкатегория")
    quantity = models.PositiveIntegerField(default=0, verbose_name="Количество")
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Себестоимость")
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена продажи")
    photo = models.ImageField(upload_to='products/photos/', blank=True, null=True, verbose_name="Фото")
    qr_code = models.ImageField(upload_to='products/qr_codes/', blank=True, null=True, verbose_name="QR-код")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, verbose_name="Склад")
    owner = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Владелец")
    is_archived = models.BooleanField(default=False, verbose_name="Архивировано")

    def save(self, *args, **kwargs):
        if not self.unique_id:
            self.unique_id = str(uuid.uuid4())[:50]
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

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"

############
### CART ###
############

class Cart(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Владелец")
    number = models.PositiveIntegerField(verbose_name="Номер корзины", editable=False)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Корзина"
        verbose_name_plural = "Корзины"
        constraints = [
            models.UniqueConstraint(fields=['owner', 'number'], name='unique_cart_number_per_owner')
        ]

    def save(self, *args, **kwargs):
        if not self.number:
            max_number = Cart.objects.filter(owner=self.owner).aggregate(models.Max('number'))['number__max']
            self.number = (max_number or 0) + 1
        super().save(*args, **kwargs)

    def calculate_totals(self):
        items = self.items.all()
        base_total = sum(item.base_price_total for item in items)
        actual_total = sum(item.actual_price_total for item in items)
        return base_total, actual_total

    def __str__(self):
        return f"Корзина №{self.number} пользователя {self.owner.username} от {self.created_at}"

#################
### CART ITEM ###
#################

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items', verbose_name="Корзина")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Товар")
    quantity = models.PositiveIntegerField(verbose_name="Количество")
    base_price_total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Базовая стоимость")
    actual_price_total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Фактическая стоимость")

    class Meta:
        verbose_name = "Элемент корзины"
        verbose_name_plural = "Элементы корзины"
        constraints = [
            models.UniqueConstraint(fields=['cart', 'product'], name='unique_cart_product')
        ]

    def __str__(self):
        return f"{self.quantity} x {self.product.name} в корзине №{self.cart.number}"

############
### SALE ###
############

class Sale(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Владелец")
    number = models.PositiveIntegerField(verbose_name="Номер продажи", editable=False)
    date = models.DateTimeField(auto_now_add=True, verbose_name="Дата")

    class Meta:
        verbose_name = "Продажа"
        verbose_name_plural = "Продажи"
        constraints = [
            models.UniqueConstraint(fields=['owner', 'number'], name='unique_sale_number_per_owner')
        ]

    def save(self, *args, **kwargs):
        if not self.number:
            max_number = Sale.objects.filter(owner=self.owner).aggregate(models.Max('number'))['number__max']
            self.number = (max_number or 0) + 1
        super().save(*args, **kwargs)

    def calculate_totals(self):
        items = self.items.all()
        base_total = sum(item.base_price_total for item in items)
        actual_total = sum(item.actual_price_total for item in items)
        return base_total, actual_total

    def __str__(self):
        return f"Продажа №{self.number} от {self.date}"

#################
### SALE ITEM ###
#################

class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items', verbose_name="Продажа")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Товар")
    quantity = models.PositiveIntegerField(verbose_name="Количество")
    base_price_total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Базовая стоимость")
    actual_price_total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Фактическая стоимость")

    class Meta:
        verbose_name = "Элемент продажи"
        verbose_name_plural = "Элементы продажи"

    def __str__(self):
        return f"{self.quantity} x {self.product.name} в продаже №{self.sale.number}"

##############
### RETURN ###
##############

class Return(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='returns', verbose_name="Продажа")
    sale_item = models.ForeignKey(SaleItem, on_delete=models.CASCADE, related_name='returns', verbose_name="Элемент продажи")
    quantity = models.PositiveIntegerField(verbose_name="Количество")
    returned_at = models.DateTimeField(default=timezone.now, verbose_name="Дата возврата")
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='returns', verbose_name="Владелец")

    class Meta:
        verbose_name = "Возврат"
        verbose_name_plural = "Возвраты"

    def __str__(self):
        return f"Возврат {self.quantity} x {self.sale_item.product.name} из продажи №{self.sale.number}"

#####################
### USER SETTINGS ###
#####################

class UserSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    hide_cost_price = models.BooleanField(default=False, verbose_name="Скрыть себестоимость")
    is_pending = models.BooleanField(default=True, verbose_name="Ожидает подтверждения")

    class Meta:
        verbose_name = "Настройки пользователя"
        verbose_name_plural = "Настройки пользователей"

#################
### LOG ENTRY ###
#################

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
        ('RETURN', 'Возврат'),
        ('FAILED_LOGIN', 'Неудачная попытка входа'),
    )

    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Время")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='inventory_log_entries', verbose_name="Пользователь")
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES, verbose_name="Тип действия")
    message = models.TextField(verbose_name="Сообщение")

    def __str__(self):
        return f"{self.timestamp} - {self.get_action_type_display()} - {self.message}"

    class Meta:
        verbose_name = "Запись лога"
        verbose_name_plural = "Записи логов"