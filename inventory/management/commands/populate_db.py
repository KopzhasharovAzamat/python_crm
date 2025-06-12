import os
from django.core.management.base import BaseCommand
from django.core.files import File
from inventory.models import RoomType, FurnitureType, Product, ProductImage, Feedback, Review
from django.conf import settings

class Command(BaseCommand):
    help = 'Populate the database with initial data'

    def handle(self, *args, **kwargs):
        self.stdout.write("Начало заполнения базы данных...")

        # Очистка базы данных (опционально, удалите, если не нужно)
        self.stdout.write("Очистка существующих данных...")
        Review.objects.all().delete()
        Feedback.objects.all().delete()
        ProductImage.objects.all().delete()
        Product.objects.all().delete()
        FurnitureType.objects.all().delete()
        RoomType.objects.all().delete()

        # Типы комнат
        rooms = ['Спальня', 'Гостиная', 'Кухня']
        room_objects = {}
        for room in rooms:
            room_obj, created = RoomType.objects.get_or_create(name=room)
            room_objects[room] = room_obj
            self.stdout.write(self.style.SUCCESS(f'Добавлен тип комнаты: {room}'))

        # Типы мебели
        furniture_types = [
            ('Спальный гарнитур', 'Спальня'),
            ('Диван', 'Гостиная'),
            ('Кухонный гарнитур', 'Кухня'),
        ]
        furniture_objects = {}
        for furniture, room in furniture_types:
            furniture_obj, created = FurnitureType.objects.get_or_create(
                name=furniture,
                room_type=room_objects[room]
            )
            furniture_objects[furniture] = furniture_obj
            self.stdout.write(self.style.SUCCESS(f'Добавлен тип мебели: {furniture}'))

        # Товары и фотографии
        products_data = {
            'Спальный гарнитур': [
                {'name': 'Спальный гарнитур Lux', 'description': 'Элегантный гарнитур для спальни.', 'price': 65000, 'rating': 4.8},
                {'name': 'Спальный гарнитур Relax', 'description': 'Комфорт и стиль для сна.', 'price': 60000, 'rating': 4.7},
                {'name': 'Спальный гарнитур Milan', 'description': 'Роскошь и уют.', 'price': 70000, 'rating': 4.9},
                {'name': 'Спальный гарнитур Modern', 'description': 'Современный дизайн.', 'price': 68000, 'rating': 4.6},
                {'name': 'Спальный гарнитур Classic', 'description': 'Классика для спальни.', 'price': 62000, 'rating': 4.5},
            ],
            'Диван': [
                {'name': 'Диван Loft', 'description': 'Стильный диван для гостиной.', 'price': 45000, 'rating': 4.8},
                {'name': 'Диван Comfort', 'description': 'Уют и комфорт.', 'price': 42000, 'rating': 4.7},
                {'name': 'Диван Luxe', 'description': 'Элегантный велюровый диван.', 'price': 48000, 'rating': 4.9},
                {'name': 'Диван Modern', 'description': 'Современный раскладной диван.', 'price': 46000, 'rating': 4.6},
                {'name': 'Диван Classic', 'description': 'Классический дизайн.', 'price': 43000, 'rating': 4.5},
            ],
            'Кухонный гарнитур': [
                {'name': 'Кухня Royal', 'description': 'Роскошь для кухни.', 'price': 95000, 'rating': 4.8},
                {'name': 'Кухня Comfort', 'description': 'Функциональность и стиль.', 'price': 90000, 'rating': 4.7},
                {'name': 'Кухня Luxe', 'description': 'Премиальный кухонный гарнитур.', 'price': 100000, 'rating': 4.9},
                {'name': 'Кухня Modern', 'description': 'Современный минимализм.', 'price': 92000, 'rating': 4.6},
                {'name': 'Кухня Classic', 'description': 'Классический кухонный гарнитур.', 'price': 88000, 'rating': 4.5},
            ],
        }

        folder_map = {
            'Спальный гарнитур': 'spalnya',
            'Диван': 'gostinnaya',
            'Кухонный гарнитур': 'kuhnya',
        }

        for furniture_type, products in products_data.items():
            folder_name = folder_map[furniture_type]
            photo_dir = os.path.join(settings.MEDIA_ROOT, 'products', 'photos', folder_name)
            self.stdout.write(f"Проверяю директорию: {photo_dir}")

            if not os.path.exists(photo_dir):
                self.stdout.write(self.style.WARNING(f'Директория {photo_dir} не существует, фотографии не будут добавлены.'))
                continue

            for index, product_data in enumerate(products, 1):
                product = Product.objects.create(
                    name=product_data['name'],
                    description=product_data['description'],
                    furniture_type=furniture_objects[furniture_type],
                    price=product_data['price'],
                    rating=product_data['rating'],
                    views=0
                )
                self.stdout.write(self.style.SUCCESS(f'Добавлен товар: {product.name}'))

                # Добавление фотографий
                for i in range(1, 4):  # Пробуем добавить 2-3 фотографии
                    photo_path = os.path.join(photo_dir, f'{folder_name}_{index}_{i}.jpg')
                    self.stdout.write(f"Проверяю фото: {photo_path}")
                    if os.path.exists(photo_path):
                        with open(photo_path, 'rb') as f:
                            product_image = ProductImage(product=product)
                            product_image.image.save(
                                f'{folder_name}_{index}_{i}.jpg',
                                File(f),
                                save=True
                            )
                        self.stdout.write(self.style.SUCCESS(f'Добавлена фотография: {photo_path}'))
                    else:
                        self.stdout.write(self.style.WARNING(f'Фото не найдено: {photo_path}'))

        # Сообщения обратной связи
        feedback_data = [
            {'name': 'Анна', 'email': 'anna@example.com', 'message': 'Отличный магазин, быстрая доставка!'},
            {'name': 'Игорь', 'email': 'igor@example.com', 'message': 'Качественная мебель, доволен покупкой.'},
            {'name': 'Елена', 'email': 'elena@example.com', 'message': 'Хочу уточнить сроки доставки.'},
            {'name': 'Михаил', 'email': 'mikhail@example.com', 'message': 'Отличный сервис, рекомендую!'},
        ]
        for feedback in feedback_data:
            Feedback.objects.create(**feedback)
            self.stdout.write(self.style.SUCCESS(f'Добавлено сообщение: {feedback["name"]}'))

        # Отзывы
        reviews_data = [
            {'name': 'Кымбат', 'city': 'Москва', 'avatar': 'rus7.jpeg', 'review': 'Купил диван, качество на высоте!'},
            {'name': 'Мария Петрова', 'city': 'Санкт-Петербург', 'avatar': 'rus8.jpeg', 'review': 'Обеденный стол великолепен.'},
            {'name': 'Иван Смирнов', 'city': 'Екатеринбург', 'avatar': 'rus1.jpeg', 'review': 'Кресло очень удобное.'},
            {'name': 'Ольга Кузнецова', 'city': 'Новосибирск', 'avatar': 'rus9.jpg', 'review': 'Кухонный гарнитур идеален.'},
            {'name': 'Дмитрий Васильев', 'city': 'Казань', 'avatar': 'rus2.jpg', 'review': 'Стулья и диван отличные.'},
            {'name': 'Юлия Александрова', 'city': 'Челябинск', 'avatar': 'rus10.webp', 'review': 'Шкаф функциональный.'},
            {'name': 'Анатолий Григорьев', 'city': 'Ростов-на-Дону', 'avatar': 'rus44.jpg', 'review': 'Комод качественный.'},
            {'name': 'Екатерина Сидорова', 'city': 'Самара', 'avatar': 'rus5.jpeg', 'review': 'Спальный гарнитур шикарный.'},
            {'name': 'Сергей Иванов', 'city': 'Омск', 'avatar': 'rus3.jpg', 'review': 'Ванная мебель стильная.'},
        ]
        review_dir = os.path.join(settings.MEDIA_ROOT, 'reviews')
        if not os.path.exists(review_dir):
            self.stdout.write(self.style.WARNING(f'Директория {review_dir} не существует, аватары не будут добавлены.'))

        for review in reviews_data:
            review_obj = Review.objects.create(
                name=review['name'],
                city=review['city'],
                review=review['review']
            )
            avatar_path = os.path.join(review_dir, review['avatar'])
            self.stdout.write(f"Проверяю аватар: {avatar_path}")
            if os.path.exists(avatar_path):
                with open(avatar_path, 'rb') as f:
                    review_obj.avatar.save(review['avatar'], File(f), save=True)
                self.stdout.write(self.style.SUCCESS(f'Добавлен аватар: {avatar_path}'))
            else:
                self.stdout.write(self.style.WARNING(f'Аватар не найден: {avatar_path}'))
            self.stdout.write(self.style.SUCCESS(f'Добавлен отзыв: {review["name"]}'))

        self.stdout.write(self.style.SUCCESS("База данных успешно заполнена!"))