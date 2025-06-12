# CRM System
CRM-система для мебельного магазина.

## Установка и запуск
1. Клонируйте репозиторий.
2. Создайте виртуальное окружение `python -m venv venv`.
3. Перейдите в виртуальное окружение `venv\Scripts\activate`.
4. Установите зависимости: `pip install -r requirements.txt`.
5. Создание миграций: `python manage.py makemigrations`
6. Выполните миграции: `python manage.py migrate`. 
7. Заполните базу данных (опционально): `python manage.py populate_db`
8. Создайте супер пользователя: `python manage.py createsuperuser`
9. Запустите сервер: `python manage.py runserver`.