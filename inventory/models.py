# inventory/models.py

from django.db import models
from django.contrib.auth.models import User

class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="Тип/Категория помещения")  # Квартира/Дом/Коммерческое помещение

    def __str__(self):
        return self.name

class Style(models.Model):
    name = models.CharField(max_length=100, verbose_name="Стиль")  # Минимализм, Лофт и т.д.

    def __str__(self):
        return self.name

class Design(models.Model):
    title = models.CharField(max_length=200, verbose_name="Название проекта")
    description = models.TextField(verbose_name="Описание")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, verbose_name="Категория")
    style = models.ForeignKey(Style, on_delete=models.SET_NULL, null=True, verbose_name="Стиль")
    area = models.PositiveIntegerField(verbose_name="Площадь (м²)")
    preview = models.ImageField(upload_to='designs/previews/', verbose_name="Превью")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class DesignImage(models.Model):
    design = models.ForeignKey(Design, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to='designs/portfolio/', verbose_name="Фото проекта")

    def __str__(self):
        return f"Изображение для {self.design.title}"

class PortfolioItem(models.Model):
    design = models.OneToOneField(Design, on_delete=models.CASCADE, verbose_name="Проект")
    show_on_main = models.BooleanField(default=False, verbose_name="Показывать на главной")

class ConsultationRequest(models.Model):
    name = models.CharField(max_length=100, verbose_name="Имя")
    phone = models.CharField(max_length=30, verbose_name="Телефон")
    message = models.TextField(verbose_name="Сообщение")
    created_at = models.DateTimeField(auto_now_add=True)

class Tariff(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название пакета/тарифа")
    description = models.TextField(verbose_name="Описание тарифа")
    price = models.PositiveIntegerField(verbose_name="Цена")

    def __str__(self):
        return self.name

class Order(models.Model):
    client = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Клиент")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    style = models.ForeignKey(Style, on_delete=models.SET_NULL, null=True)
    area = models.PositiveIntegerField(verbose_name="Площадь (м²)")
    tariff = models.ForeignKey(Tariff, on_delete=models.SET_NULL, null=True, verbose_name="Пакет")
    comment = models.TextField(blank=True, null=True, verbose_name="Комментарий к заказу")
    created_at = models.DateTimeField(auto_now_add=True)
    STATUS_CHOICES = [
        ('new', 'Новый'), ('in_progress', 'В работе'), ('done', 'Выполнен'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')

class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    design = models.ForeignKey(Design, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Проект", related_name='reviews')
    text = models.TextField(verbose_name="Текст отзыва")
    created_at = models.DateTimeField(auto_now_add=True)
    client_name = models.CharField(max_length=100, blank=True, verbose_name="Имя клиента")
    city = models.CharField(max_length=100, blank=True, verbose_name="Город")
