# inventory/models.py

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class RoomType(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название типа комнаты")

    class Meta:
        verbose_name = "Типа комнаты"
        verbose_name_plural = "Типы комнат"
        ordering = ['name']

    def __str__(self):
        return self.name

class FurnitureType(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название мебели")
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE, verbose_name="Тип комнаты")

    class Meta:
        verbose_name = "Тип мебели"
        verbose_name_plural = "Типы мебели"
        ordering = ['name']

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=200, verbose_name="Название")
    description = models.TextField(verbose_name="Описание")
    furniture_type = models.ForeignKey(FurnitureType, on_delete=models.CASCADE, verbose_name="Тип мебели")
    price = models.FloatField(verbose_name="Цена", validators=[MinValueValidator(0.0)])
    rating = models.FloatField(
        verbose_name="Рейтинг",
        validators=[MinValueValidator(1.0), MaxValueValidator(5.0)],
        default=1.0
    )
    views = models.PositiveIntegerField(verbose_name="Количество просмотров", default=0)

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ['name']

    def __str__(self):
        return self.name

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images', verbose_name="Товар")
    image = models.ImageField(upload_to='products/photos/', verbose_name="Фото")

    class Meta:
        verbose_name = "Фото товара"
        verbose_name_plural = "Фото товаров"

    def __str__(self):
        return f"Фото {self.product.name}"

class Feedback(models.Model):
    name = models.CharField(max_length=100, verbose_name="Имя")
    email = models.EmailField(verbose_name="Email")
    message = models.TextField(verbose_name="Текст сообщения")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Обратная связь"
        verbose_name_plural = "Сообщения обратной связи"
        ordering = ['-created_at']

    def __str__(self):
        return f"Сообщение ({self.name} {self.email})"

class Review(models.Model):
    name = models.CharField(max_length=100, verbose_name="Имя")
    city = models.CharField(max_length=100, verbose_name="Город")
    avatar = models.ImageField(upload_to='reviews/', verbose_name="Аватар", blank=True, null=True)
    review = models.TextField(verbose_name="Отзыв")

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        ordering = ['name']

    def __str__(self):
        return f"Отзыв от {self.name} ({self.city})"