# inventory/views.py
import uuid
import json
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Sum, Q, F, Value, FloatField
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import timedelta
from .forms import RegisterForm, ProductForm, WarehouseForm, UserChangeForm, UserSettingsForm, CategoryForm, \
    SubcategoryForm, CartItemForm, ReturnForm, SaleItemForm, LoginForm
from .models import Product, Warehouse, Sale, SaleItem, Cart, CartItem, Category, Subcategory, UserSettings, User, \
    Return, LogEntry, CartComment, SaleComment
from django.http import JsonResponse

# Helper function to log actions
def create_log_entry(user, action_type, message):
    LogEntry.objects.create(user=user, action_type=action_type, message=message)

######################
### LOGIN / LOGOUT ###
######################

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                create_log_entry(user, 'LOGIN', f'Пользователь {user.username} вошёл в систему')
                return redirect('products')
            else:
                create_log_entry(None, 'FAILED_LOGIN', f'Неудачная попытка входа для пользователя {username}')
                messages.error(request, 'Неверный логин или пароль.')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    user = request.user
    if user.is_authenticated:
        create_log_entry(user, 'LOGOUT', f'Пользователь {user.username} вышел из системы')
    logout(request)
    messages.success(request, 'Вы вышли из системы.')
    return redirect('login')

################
### REGISTER ###
################

def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = User(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                first_name=form.cleaned_data['first_name'],
                is_active=False
            )
            user.set_password(form.cleaned_data['password'])
            user.save()
            UserSettings.objects.create(user=user, is_pending=True)
            create_log_entry(user, 'REGISTER', f'Новый пользователь {user.username} зарегистрирован и ожидает подтверждения')
            messages.success(request, 'Регистрация успешна! Ожидайте подтверждения администратором.')
            return redirect('login')
        else:
            messages.error(request, 'Ошибка при регистрации. Проверьте данные.')
    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})

###############
### PROFILE ###
###############

@login_required
def profile(request):
    user_settings, created = UserSettings.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        user_form = UserChangeForm(request.POST, instance=request.user)
        settings_form = UserSettingsForm(request.POST, instance=user_settings)
        if user_form.is_valid() and settings_form.is_valid():
            user_form.save()
            settings_form.save()
            create_log_entry(request.user, 'UPDATE', f'Пользователь {request.user.username} обновил свой профиль')
            messages.success(request, 'Профиль обновлен.')
            return redirect('profile')
    else:
        user_form = UserChangeForm(instance=request.user)
        settings_form = UserSettingsForm(instance=user_settings)
    return render(request, 'profile.html', {'user_form': user_form, 'settings_form': settings_form})

###############
### PRODUCT ###
###############

@login_required
def product_list(request):
    query = request.GET.get('q', '')
    category = request.GET.get('category', '')
    subcategory = request.GET.get('subcategory', '')
    warehouse = request.GET.get('warehouse', '')
    min_quantity = request.GET.get('min_quantity', '')
    sort_by = request.GET.get('sort_by', '')

    products = Product.objects.filter(owner=request.user, is_archived=False)

    if query:
        try:
            uuid_obj = uuid.UUID(query)
            products = products.filter(unique_id=query)
        except ValueError:
            products = products.filter(Q(name__icontains=query) | Q(subcategory__name__icontains=query))
    if category:
        products = products.filter(category__name=category)
    if subcategory:
        products = products.filter(subcategory__name=subcategory)
    if warehouse:
        products = products.filter(warehouse__name=warehouse)
    if min_quantity:
        products = products.filter(quantity__gte=min_quantity)

    # Ensure consistent ordering to avoid UnorderedObjectListWarning
    if sort_by:
        allowed_sort_fields = [
            'name', '-name',
            'category__name', '-category__name',
            'subcategory__name', '-subcategory__name',
            'selling_price', '-selling_price',
            'quantity', '-quantity',
            'warehouse__name', '-warehouse__name'
        ]
        if sort_by in allowed_sort_fields:
            products = products.order_by(sort_by)
        else:
            products = products.order_by('name')
    else:
        products = products.order_by('name')  # Default ordering

    # Пагинация
    paginator = Paginator(products, 10)  # 10 товаров на страницу
    page_number = request.GET.get('page', 1)
    try:
        products_paginated = paginator.page(page_number)
    except PageNotAnInteger:
        products_paginated = paginator.page(1)
    except EmptyPage:
        products_paginated = paginator.page(paginator.num_pages)

    categories = Category.objects.filter(owner=request.user).select_related('owner')
    subcategories = Subcategory.objects.filter(owner=request.user).select_related('owner')
    warehouses = Warehouse.objects.filter(owner=request.user).select_related('owner')
    low_stock_message = request.session.pop('low_stock', None)

    return render(request, 'products.html', {
        'products': products_paginated,
        'categories': categories,
        'subcategories': subcategories,
        'warehouses': warehouses,
        'low_stock_message': low_stock_message,
    })

@login_required
def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id, owner=request.user)
    user_settings, created = UserSettings.objects.get_or_create(user=request.user)
    show_cost_price = not user_settings.hide_cost_price
    return render(request, 'product_detail.html', {
        'product': product,
        'show_cost_price': show_cost_price,
    })

@login_required
def product_add(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            product = form.save(commit=False)
            product.owner = request.user
            product.save()
            create_log_entry(request.user, 'ADD', f'Товар "{product.name}" добавлен пользователем {request.user.username}')
            if product.quantity < 5:
                messages.warning(request, f"Товар {product.name} заканчивается (осталось {product.quantity})")
            return redirect('products')
        else:
            # Если форма не валидна, передаём её обратно в шаблон с ошибками
            form.fields['warehouse'].queryset = Warehouse.objects.filter(owner=request.user)
            return render(request, 'product_form.html', {'form': form})
    else:
        form = ProductForm(user=request.user)
        form.fields['warehouse'].queryset = Warehouse.objects.filter(owner=request.user)
    return render(request, 'product_form.html', {'form': form})

@login_required
def product_edit(request, product_id):
    product = get_object_or_404(Product, id=product_id, owner=request.user)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product, user=request.user)
        if form.is_valid():
            product = form.save()
            create_log_entry(request.user, 'UPDATE', f'Товар "{product.name}" обновлён пользователем {request.user.username}')
            if product.quantity < 5:
                messages.warning(request, f"Товар {product.name} заканчивается (осталось {product.quantity})")
            return redirect('products')
    else:
        form = ProductForm(instance=product, user=request.user)
        form.fields['warehouse'].queryset = Warehouse.objects.filter(owner=request.user)
    return render(request, 'product_form.html', {'form': form})

@login_required
def product_delete(request, product_id):
    product = get_object_or_404(Product, id=product_id, owner=request.user)
    if request.method == 'POST':
        product_name = product.name
        product.delete()
        create_log_entry(request.user, 'DELETE', f'Товар "{product_name}" удалён пользователем {request.user.username}')
        messages.success(request, f'Товар "{product_name}" удален.')
    return redirect('products')

@login_required
def get_product_price(request):
    if request.method == 'GET':
        product_id = request.GET.get('product_id')
        try:
            product = Product.objects.get(id=product_id, owner=request.user)
            return JsonResponse({
                'id': product.id,
                'name': product.name,
                'category': product.category.name if product.category else '',
                'subcategory': product.subcategory.name if product.subcategory else '',
                'warehouse': product.warehouse.name if product.warehouse else '',
                'quantity': product.quantity,
                'selling_price': float(product.selling_price),
                'photo': product.photo.url if product.photo else '',
            })
        except Product.DoesNotExist:
            return JsonResponse({'error': 'Товар не найден'}, status=404)
    return JsonResponse({'error': 'Неверный метод запроса'}, status=400)

###############
### ARCHIVE ###
###############

@login_required
def archived_products(request):
    # Ensure consistent ordering
    products = Product.objects.filter(owner=request.user, is_archived=True).order_by('name')

    # Пагинация
    paginator = Paginator(products, 10)  # 10 товаров на страницу
    page_number = request.GET.get('page', 1)
    try:
        products_paginated = paginator.page(page_number)
    except PageNotAnInteger:
        products_paginated = paginator.page(1)
    except EmptyPage:
        products_paginated = paginator.page(paginator.num_pages)

    return render(request, 'archived_products.html', {
        'products': products_paginated,
    })

@login_required
def product_archive(request, product_id):
    product = get_object_or_404(Product, id=product_id, owner=request.user)
    if request.method == 'POST':
        product.is_archived = True
        product.save()
        create_log_entry(request.user, 'UPDATE', f'Товар "{product.name}" архивирован пользователем {request.user.username}')
        messages.success(request, f'Товар "{product.name}" архивирован.')
    return redirect('products')

@login_required
def product_unarchive(request, product_id):
    product = get_object_or_404(Product, id=product_id, owner=request.user)
    if request.method == 'POST':
        product.is_archived = False
        product.save()
        create_log_entry(request.user, 'UPDATE', f'Товар "{product.name}" разархивирован пользователем {request.user.username}')
        messages.success(request, f'Товар "{product.name}" разархивирован.')
    return redirect('archived_products')

#################
### WAREHOUSE ###
#################

@login_required
def warehouse_list(request):
    if request.method == 'POST':
        if 'name' in request.POST:
            form = WarehouseForm(request.POST)
            if form.is_valid():
                warehouse = form.save(commit=False)
                warehouse.owner = request.user
                warehouse.save()
                create_log_entry(request.user, 'ADD', f'Склад "{warehouse.name}" добавлен пользователем {request.user.username}')
                messages.success(request, 'Склад добавлен.')
                return redirect('warehouses')
        elif 'warehouse_id' in request.POST and request.POST.get('action') == 'delete':
            warehouse = get_object_or_404(Warehouse, id=request.POST['warehouse_id'], owner=request.user)
            warehouse_name = warehouse.name
            warehouse.delete()
            create_log_entry(request.user, 'DELETE', f'Склад "{warehouse_name}" удалён пользователем {request.user.username}')
            messages.success(request, 'Склад удален.')
            return redirect('warehouses')
    warehouses = Warehouse.objects.filter(owner=request.user).order_by('name')  # Ensure ordering
    form = WarehouseForm()
    return render(request, 'warehouses.html', {'warehouses': warehouses, 'form': form})

@login_required
def warehouse_add(request):
    if request.method == 'POST':
        form = WarehouseForm(request.POST)
        if form.is_valid():
            warehouse = form.save(commit=False)
            warehouse.owner = request.user
            warehouse.save()
            create_log_entry(request.user, 'ADD', f'Склад "{warehouse.name}" добавлен пользователем {request.user.username}')
            return redirect('warehouses')
    else:
        form = WarehouseForm()
    return render(request, 'warehouse_form.html', {'form': form})

@login_required
def warehouse_edit(request, warehouse_id):
    warehouse = get_object_or_404(Warehouse, id=warehouse_id, owner=request.user)
    if request.method == 'POST':
        form = WarehouseForm(request.POST, instance=warehouse)
        if form.is_valid():
            form.save()
            create_log_entry(request.user, 'UPDATE', f'Склад "{warehouse.name}" обновлён пользователем {request.user.username}')
            messages.success(request, 'Название склада обновлено.')
            return redirect('warehouses')
    else:
        form = WarehouseForm(instance=warehouse)
    return render(request, 'warehouse_form.html', {'form': form, 'warehouse': warehouse})

@login_required
def warehouse_delete(request, warehouse_id):
    warehouse = get_object_or_404(Warehouse, id=warehouse_id, owner=request.user)
    if request.method == 'POST':
        warehouse_name = warehouse.name
        warehouse.delete()
        create_log_entry(request.user, 'DELETE', f'Склад "{warehouse_name}" удалён пользователем {request.user.username}')
        messages.success(request, f'Склад "{warehouse_name}" удален.')
        return redirect('warehouses')
    return redirect('warehouses')

############
### SALE ###
############

@login_required
def sales_list(request):
    sales = Sale.objects.filter(owner=request.user).prefetch_related('items__product', 'comments')

    product_name = request.GET.get('product_name', '')
    warehouse = request.GET.get('warehouse', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    min_amount = request.GET.get('min_amount', '')
    max_amount = request.GET.get('max_amount', '')
    min_quantity = request.GET.get('min_quantity', '')
    max_quantity = request.GET.get('max_quantity', '')
    sort_by = request.GET.get('sort_by', '')

    if product_name:
        sales = sales.filter(items__product__name__icontains=product_name)
    if warehouse:
        sales = sales.filter(items__product__warehouse__name=warehouse)
    if date_from:
        try:
            date_from = timezone.datetime.strptime(date_from, '%Y-%m-%d')
            sales = sales.filter(date__gte=date_from)
        except ValueError:
            messages.error(request, 'Неверный формат даты "с". Используйте YYYY-MM-DD.')
    if date_to:
        try:
            date_to = timezone.datetime.strptime(date_to, '%Y-%m-%d')
            date_to = date_to + timedelta(days=1)
            sales = sales.filter(date__lt=date_to)
        except ValueError:
            messages.error(request, 'Неверный формат даты "по". Используйте YYYY-MM-DD.')
    if min_amount or max_amount:
        sales = sales.annotate(total_amount=Sum('items__actual_price_total'))
        if min_amount:
            try:
                min_amount = float(min_amount)
                sales = sales.filter(total_amount__gte=min_amount)
            except ValueError:
                messages.error(request, 'Минимальная сумма должна быть числом.')
        if max_amount:
            try:
                max_amount = float(max_amount)
                sales = sales.filter(total_amount__lte=max_amount)
            except ValueError:
                messages.error(request, 'Максимальная сумма должна быть числом.')
    if min_quantity or max_quantity:
        sales = sales.annotate(total_quantity=Sum('items__quantity'))
        if min_quantity:
            try:
                min_quantity = int(min_quantity)
                sales = sales.filter(total_quantity__gte=min_quantity)
            except ValueError:
                messages.error(request, 'Минимальное количество должно быть целым числом.')
        if max_quantity:
            try:
                max_quantity = int(max_quantity)
                sales = sales.filter(total_quantity__lte=max_quantity)
            except ValueError:
                messages.error(request, 'Максимальное количество должно быть целым числом.')

    # Ensure consistent ordering
    allowed_sort_fields = [
        'date', '-date',
        'items__product__name', '-items__product__name',
        'items__quantity', '-items__quantity',
        'items__product__warehouse__name', '-items__product__warehouse__name',
        'items__actual_price_total', '-items__actual_price_total'
    ]
    if sort_by in allowed_sort_fields:
        sales = sales.order_by(sort_by)
    else:
        sales = sales.order_by('-date')  # Default ordering

    # Пагинация
    paginator = Paginator(sales, 10)  # 10 продаж на страницу
    page_number = request.GET.get('page', 1)
    try:
        sales_paginated = paginator.page(page_number)
    except PageNotAnInteger:
        sales_paginated = paginator.page(1)
    except EmptyPage:
        sales_paginated = paginator.page(paginator.num_pages)

    warehouses = Warehouse.objects.filter(owner=request.user).order_by('name')

    return render(request, 'sales_list.html', {
        'sales': sales_paginated,
        'warehouses': warehouses,
        'product_name': product_name,
        'warehouse': warehouse,
        'date_from': date_from,
        'date_to': date_to,
        'min_amount': min_amount,
        'max_amount': max_amount,
        'min_quantity': min_quantity,
        'max_quantity': max_quantity,
        'sort_by': sort_by,
    })

@login_required
def sale_detail(request, sale_id):
    sale = get_object_or_404(Sale, id=sale_id, owner=request.user)
    items = sale.items.all()
    comments = sale.comments.all()
    base_total, actual_total = sale.calculate_totals()
    return render(request, 'sale_detail.html', {
        'sale': sale,
        'items': items,
        'comments': comments,
        'base_total': base_total,
        'actual_total': actual_total
    })

@login_required
def sale_edit(request, sale_id):
    sale = get_object_or_404(Sale, id=sale_id, owner=request.user)
    products = Product.objects.filter(owner=request.user).order_by('name')

    form = SaleItemForm()
    form.fields['product'].queryset = products

    if request.method == 'POST':
        if 'add_item' in request.POST:
            form = SaleItemForm(request.POST)
            if form.is_valid():
                sale_item = form.save(commit=False)
                product = sale_item.product
                sale_item.sale = sale
                sale_item.base_price_total = sale_item.quantity * product.selling_price
                actual_price = form.cleaned_data['actual_price'] or product.selling_price
                sale_item.actual_price_total = sale_item.quantity * actual_price

                if sale_item.quantity <= product.quantity:
                    product.quantity -= sale_item.quantity
                    product.save()
                    sale_item.save()
                    create_log_entry(request.user, 'UPDATE', f'Товар "{product.name}" (кол-во: {sale_item.quantity}) добавлен в продажу №{sale.number} пользователем {request.user.username}')
                    messages.success(request, f'Товар "{product.name}" добавлен в продажу.')
                    return redirect('sale_edit', sale_id=sale.id)
                else:
                    messages.error(request, 'Недостаточно товара на складе.')
        elif 'delete_item' in request.POST:
            item_id = request.POST.get('item_id')
            sale_item = get_object_or_404(SaleItem, id=item_id, sale=sale)
            product = sale_item.product
            product.quantity += sale_item.quantity
            product.save()
            sale_item.delete()
            create_log_entry(request.user, 'UPDATE', f'Товар "{product.name}" (кол-во: {sale_item.quantity}) удалён из продажи №{sale.number} пользователем {request.user.username}')
            messages.success(request, f'Товар "{product.name}" удалён из продажи.')
            return redirect('sale_edit', sale_id=sale.id)

    return render(request, 'sale_edit.html', {
        'sale': sale,
        'form': form,
        'products': products
    })

@login_required
def return_item(request, sale_id, item_id):
    sale = get_object_or_404(Sale, id=sale_id, owner=request.user)
    sale_item = get_object_or_404(SaleItem, id=item_id, sale=sale)

    if request.method == 'POST':
        form = ReturnForm(request.POST)
        if form.is_valid():
            return_quantity = form.cleaned_data['quantity']
            if return_quantity > sale_item.quantity:
                messages.error(request, 'Нельзя вернуть больше, чем было продано.')
                return redirect('sale_detail', sale_id=sale.id)

            return_record = Return.objects.create(
                sale=sale,
                sale_item=sale_item,
                quantity=return_quantity,
                owner=request.user
            )

            sale_item.quantity -= return_quantity
            if sale_item.quantity == 0:
                sale_item.delete()
            else:
                sale_item.base_price_total = sale_item.quantity * sale_item.product.selling_price
                sale_item.actual_price_total = sale_item.quantity * (sale_item.actual_price_total / (sale_item.quantity + return_quantity))
                sale_item.save()

            product = sale_item.product
            product.quantity += return_quantity
            product.save()

            create_log_entry(request.user, 'RETURN', f'Возврат {return_quantity} x "{product.name}" из продажи №{sale.number} пользователем {request.user.username}')
            messages.success(request, f'Возвращено {return_quantity} шт. товара "{product.name}".')
            return redirect('sale_detail', sale_id=sale.id)
    else:
        form = ReturnForm()

    return render(request, 'return_item.html', {
        'sale': sale,
        'sale_item': sale_item,
        'form': form
    })

@login_required
def sale_comment_add(request, sale_id):
    sale = get_object_or_404(Sale, id=sale_id, owner=request.user)
    if request.method == 'POST':
        comment_text = request.POST.get('comment_text', '').strip()
        if comment_text:
            comment = SaleComment.objects.create(sale=sale, text=comment_text)
            create_log_entry(request.user, 'ADD', f'Комментарий к продаже №{sale.number} добавлен пользователем {request.user.username}')
            messages.success(request, 'Комментарий добавлен.')
        else:
            messages.error(request, 'Комментарий не может быть пустым.')
    return redirect('sale_detail', sale_id=sale.id)

@login_required
def sale_comment_edit(request, sale_id, comment_id):
    sale = get_object_or_404(Sale, id=sale_id, owner=request.user)
    comment = get_object_or_404(SaleComment, id=comment_id, sale=sale)
    if request.method == 'POST':
        comment_text = request.POST.get('comment_text', '').strip()
        if comment_text:
            comment.text = comment_text
            comment.save()
            create_log_entry(request.user, 'UPDATE', f'Комментарий к продаже №{sale.number} обновлён пользователем {request.user.username}')
            messages.success(request, 'Комментарий обновлён.')
        else:
            messages.error(request, 'Комментарий не может быть пустым.')
    return redirect('sale_detail', sale_id=sale.id)

@login_required
def sale_comment_delete(request, sale_id, comment_id):
    sale = get_object_or_404(Sale, id=sale_id, owner=request.user)
    comment = get_object_or_404(SaleComment, id=comment_id, sale=sale)
    if request.method == 'POST':
        comment.delete()
        create_log_entry(request.user, 'DELETE', f'Комментарий к продаже №{sale.number} удалён пользователем {request.user.username}')
        messages.success(request, 'Комментарий удалён.')
    return redirect('sale_detail', sale_id=sale.id)

############
### CART ###
############

@login_required
def cart_list(request):
    carts = Cart.objects.filter(owner=request.user).prefetch_related('items__product', 'comments')

    hide_empty = request.GET.get('hide_empty', 'off') == 'on'
    sort_by = request.GET.get('sort_by', '')

    if hide_empty:
        carts = carts.filter(items__isnull=False).distinct()

    carts = carts.annotate(
        total_cost=Coalesce(
            Sum('items__actual_price_total'),
            Value(0.0),
            output_field=FloatField()
        )
    )

    # Ensure consistent ordering
    allowed_sort_fields = [
        'number', '-number',
        'created_at', '-created_at',
        'total_cost', '-total_cost'
    ]
    if sort_by in allowed_sort_fields:
        carts = carts.order_by(sort_by)
    else:
        carts = carts.order_by('-created_at')  # Default ordering

    # Пагинация
    paginator = Paginator(carts, 10)  # 10 корзин на страницу
    page_number = request.GET.get('page', 1)
    try:
        carts_paginated = paginator.page(page_number)
    except PageNotAnInteger:
        carts_paginated = paginator.page(1)
    except EmptyPage:
        carts_paginated = paginator.page(paginator.num_pages)

    return render(request, 'cart_list.html', {
        'carts': carts_paginated,
        'hide_empty': hide_empty,
        'sort_by': sort_by,
    })

@login_required
def cart_create(request):
    if request.method == 'POST':
        try:
            cart = Cart.objects.create(owner=request.user)
            create_log_entry(request.user, 'ADD', f'Новая корзина №{cart.number} создана пользователем {request.user.username}')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'cart_id': cart.id}, status=200)
            else:
                messages.success(request, f'Корзина №{cart.number} создана.')
                return redirect('cart_add_item', cart_id=cart.id)
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': f'Ошибка при создании корзины: {str(e)}'}, status=500)
            else:
                messages.error(request, f'Ошибка при создании корзины: {str(e)}')
                return redirect('cart_list')
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'error': 'Неверный метод запроса'}, status=400)
    else:
        messages.error(request, 'Неверный метод запроса.')
        return redirect('cart_list')

@login_required
def cart_add_item(request, cart_id):
    cart = get_object_or_404(Cart, id=cart_id, owner=request.user)
    products = Product.objects.filter(owner=request.user, is_archived=False).order_by('name')

    form = CartItemForm()
    form.fields['product'].queryset = products

    if request.method == 'POST':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            try:
                data = json.loads(request.body)
                product_id = data.get('product')
                quantity = int(data.get('quantity', 1))
                actual_price = float(data.get('actual_price', 0))

                try:
                    product = Product.objects.get(id=product_id, owner=request.user, is_archived=False)
                except Product.DoesNotExist:
                    return JsonResponse({'error': 'Товар не найден.'}, status=404)

                if quantity <= 0:
                    return JsonResponse({'error': 'Количество должно быть больше 0.'}, status=400)

                if quantity > product.quantity:
                    return JsonResponse({'error': f'Недостаточно товара на складе. В наличии: {product.quantity} шт.'}, status=400)

                if actual_price < 0:
                    return JsonResponse({'error': 'Фактическая цена не может быть отрицательной.'}, status=400)

                cart_item = CartItem.objects.filter(cart=cart, product=product).first()
                if cart_item:
                    cart_item.quantity += quantity
                    cart_item.base_price_total = cart_item.quantity * product.selling_price
                    cart_item.actual_price_total = cart_item.quantity * (actual_price or product.selling_price)
                    cart_item.save()
                    action_message = f'Количество товара "{product.name}" в корзине №{cart.number} увеличено на {quantity} (итого: {cart_item.quantity}) пользователем {request.user.username} через сканирование UUID'
                else:
                    cart_item = CartItem(
                        cart=cart,
                        product=product,
                        quantity=quantity,
                        base_price_total=quantity * product.selling_price,
                        actual_price_total=quantity * (actual_price or product.selling_price)
                    )
                    cart_item.save()
                    action_message = f'Товар "{product.name}" (кол-во: {quantity}) добавлен в корзину №{cart.number} пользователем {request.user.username} через сканирование UUID'

                create_log_entry(request.user, 'ADD', action_message)
                return JsonResponse({'success': True, 'cart_id': cart.id})
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Неверный формат данных.'}, status=400)
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=500)

        form = CartItemForm(request.POST)
        if form.is_valid():
            cart_item = form.save(commit=False)
            product = cart_item.product
            existing_item = CartItem.objects.filter(cart=cart, product=product).first()
            actual_price = form.cleaned_data['actual_price'] or product.selling_price

            if existing_item:
                existing_item.quantity += cart_item.quantity
                existing_item.base_price_total = existing_item.quantity * product.selling_price
                existing_item.actual_price_total = existing_item.quantity * actual_price
                existing_item.save()
                action_message = f'Количество товара "{product.name}" в корзине №{cart.number} увеличено на {cart_item.quantity} (итого: {existing_item.quantity}) пользователем {request.user.username}'
            else:
                cart_item.cart = cart
                cart_item.base_price_total = cart_item.quantity * product.selling_price
                cart_item.actual_price_total = cart_item.quantity * actual_price
                if cart_item.quantity <= product.quantity:
                    cart_item.save()
                    action_message = f'Товар "{product.name}" (кол-во: {cart_item.quantity}) добавлен в корзину №{cart.number} пользователем {request.user.username}'
                else:
                    messages.error(request, 'Недостаточно товара на складе.')
                    return redirect('cart_add_item', cart_id=cart.id)

            create_log_entry(request.user, 'ADD', action_message)
            messages.success(request, f'Товар "{product.name}" добавлен в корзину.')
            return redirect('cart_add_item', cart_id=cart.id)
        else:
            messages.error(request, 'Ошибка при добавлении товара. Проверьте данные.')
            return redirect('cart_add_item', cart_id=cart.id)

    total_quantity = sum(item.quantity for item in cart.items.all())
    base_total, actual_total = cart.calculate_totals()
    product_totals = cart.items.values('product__name').annotate(total_quantity=Sum('quantity')).order_by('product__name')

    return render(request, 'cart_form.html', {
        'form': form,
        'cart': cart,
        'products': products,
        'total_quantity': total_quantity,
        'base_total': base_total,
        'actual_total': actual_total,
        'product_totals': product_totals,
    })

@login_required
def cart_remove_item(request, cart_id, item_id):
    cart = get_object_or_404(Cart, id=cart_id, owner=request.user)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
    product_name = cart_item.product.name
    cart_item.delete()
    messages.success(request, f'Товар "{product_name}" удалён из корзины.')
    return redirect('cart_add_item', cart_id=cart.id)

@login_required
def cart_confirm(request, cart_id):
    cart = get_object_or_404(Cart, id=cart_id, owner=request.user)
    cart_items = cart.items.all()

    if not cart_items:
        messages.error(request, 'Корзина пуста. Добавьте товары перед подтверждением.')
        return redirect('cart_add_item', cart_id=cart.id)

    product_quantities = {}
    for item in cart_items:
        product = item.product
        if product.id not in product_quantities:
            product_quantities[product.id] = {'quantity': 0, 'items': []}
        product_quantities[product.id]['quantity'] += item.quantity
        product_quantities[product.id]['items'].append(item)

    for product_id, data in product_quantities.items():
        product = Product.objects.get(id=product_id)
        total_quantity = data['quantity']
        if total_quantity > product.quantity:
            messages.error(request,
                           f'Недостаточно товара "{product.name}" на складе. В корзине: {total_quantity} шт., на складе: {product.quantity} шт.')
            return redirect('cart_add_item', cart_id=cart.id)

    # Создаём продажу
    sale = Sale.objects.create(owner=request.user)

    # Переносим товары из корзины в продажу
    for product_id, data in product_quantities.items():
        product = Product.objects.get(id=product_id)
        total_quantity = data['quantity']
        product.quantity -= total_quantity
        product.save()
        for item in data['items']:
            SaleItem.objects.create(
                sale=sale,
                product=item.product,
                quantity=item.quantity,
                base_price_total=item.base_price_total,
                actual_price_total=item.actual_price_total
            )

    # Переносим комментарии из корзины в продажу
    comments = cart.comments.all()
    for comment in comments:
        SaleComment.objects.create(
            sale=sale,
            text=comment.text,
            created_at=comment.created_at,
            updated_at=comment.updated_at
        )

    create_log_entry(request.user, 'SALE', f'Продажа №{sale.number} на основе корзины №{cart.number} завершена пользователем {request.user.username}')
    cart.delete()
    messages.success(request, 'Продажа успешно завершена!')
    return redirect('sales_list')

@login_required
def cart_cancel(request, cart_id):
    cart = get_object_or_404(Cart, id=cart_id, owner=request.user)
    cart.delete()
    messages.success(request, 'Корзина отменена.')
    return redirect('products')

@login_required
def cart_delete(request, cart_id):
    cart = get_object_or_404(Cart, id=cart_id, owner=request.user)
    if request.method == 'POST':
        cart.delete()
        create_log_entry(request.user, 'DELETE', f'Корзина №{cart.number} удалена пользователем {request.user.username}')
        messages.success(request, 'Корзина удалена.')
        return redirect('cart_list')
    return redirect('cart_list')

@login_required
def cart_comment_add(request, cart_id):
    cart = get_object_or_404(Cart, id=cart_id, owner=request.user)
    if request.method == 'POST':
        comment_text = request.POST.get('comment_text', '').strip()
        if comment_text:
            comment = CartComment.objects.create(cart=cart, text=comment_text)
            create_log_entry(request.user, 'ADD', f'Комментарий к корзине №{cart.number} добавлен пользователем {request.user.username}')
            messages.success(request, 'Комментарий добавлен.')
        else:
            messages.error(request, 'Комментарий не может быть пустым.')
    return redirect('cart_add_item', cart_id=cart.id)

@login_required
def cart_comment_edit(request, cart_id, comment_id):
    cart = get_object_or_404(Cart, id=cart_id, owner=request.user)
    comment = get_object_or_404(CartComment, id=comment_id, cart=cart)
    if request.method == 'POST':
        comment_text = request.POST.get('comment_text', '').strip()
        if comment_text:
            comment.text = comment_text
            comment.save()
            create_log_entry(request.user, 'UPDATE', f'Комментарий к корзине №{cart.number} обновлён пользователем {request.user.username}')
            messages.success(request, 'Комментарий обновлён.')
        else:
            messages.error(request, 'Комментарий не может быть пустым.')
    return redirect('cart_add_item', cart_id=cart.id)

@login_required
def cart_comment_delete(request, cart_id, comment_id):
    cart = get_object_or_404(Cart, id=cart_id, owner=request.user)
    comment = get_object_or_404(CartComment, id=comment_id, cart=cart)
    if request.method == 'POST':
        comment.delete()
        create_log_entry(request.user, 'DELETE', f'Комментарий к корзине №{cart.number} удалён пользователем {request.user.username}')
        messages.success(request, 'Комментарий удалён.')
    return redirect('cart_add_item', cart_id=cart.id)

@login_required
def get_product_by_uuid(request):
    if request.method == 'GET':
        unique_id = request.GET.get('unique_id')
        try:
            product = Product.objects.get(unique_id=unique_id, owner=request.user, is_archived=False)
            return JsonResponse({
                'id': product.id,
                'name': product.name,
                'category': product.category.name if product.category else '',
                'subcategory': product.subcategory.name if product.subcategory else '',
                'warehouse': product.warehouse.name if product.warehouse else '',
                'quantity': product.quantity,
                'selling_price': float(product.selling_price),
                'photo': product.photo.url if product.photo else '',
            })
        except Product.DoesNotExist:
            return JsonResponse({'error': 'Товар не найден'}, status=404)
    return JsonResponse({'error': 'Неверный метод запроса'}, status=400)

@login_required
def get_product_by_id(request):
    if request.method == 'GET':
        product_id = request.GET.get('product_id')
        try:
            product = Product.objects.get(id=product_id, owner=request.user, is_archived=False)
            return JsonResponse({
                'id': product.id,
                'name': product.name,
                'category': product.category.name if product.category else '',
                'subcategory': product.subcategory.name if product.subcategory else '',
                'warehouse': product.warehouse.name if product.warehouse else '',
                'quantity': product.quantity,
                'selling_price': float(product.selling_price),
                'photo': product.photo.url if product.photo else '',
            })
        except Product.DoesNotExist:
            return JsonResponse({'error': 'Товар не найден'}, status=404)
        except ValueError:
            return JsonResponse({'error': 'Неверный ID товара'}, status=400)
    return JsonResponse({'error': 'Неверный метод запроса'}, status=400)


############
### SCAN ###
############

@login_required
def scan_product(request):
    unique_id = request.GET.get('code')
    try:
        product = Product.objects.get(unique_id=unique_id, owner=request.user, is_archived=False)
        return render(request, 'scan_product.html', {'product': product})
    except Product.DoesNotExist:
        return render(request, 'error.html', {'message': 'Товар не найден'})

@login_required
def scan_product_confirm(request):
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        quantity = int(request.POST.get('quantity', 1))
        actual_price = float(request.POST.get('actual_price', 0))

        try:
            product = Product.objects.get(id=product_id, owner=request.user, is_archived=False)
        except Product.DoesNotExist:
            messages.error(request, 'Товар не найден.')
            return redirect('products')

        if quantity <= 0:
            messages.error(request, 'Количество должно быть больше 0.')
            return redirect('products')

        if quantity > product.quantity:
            messages.error(request, f'Недостаточно товара на складе. В наличии: {product.quantity} шт.')
            return redirect('products')

        if actual_price < 0:
            messages.error(request, 'Фактическая цена не может быть отрицательной.')
            return redirect('products')

        cart = Cart.objects.create(owner=request.user)
        create_log_entry(request.user, 'ADD', f'Новая корзина №{cart.number} создана пользователем {request.user.username} через сканирование')

        cart_item = CartItem(
            cart=cart,
            product=product,
            quantity=quantity,
            base_price_total=quantity * product.selling_price,
            actual_price_total=quantity * (actual_price or product.selling_price)
        )
        cart_item.save()

        create_log_entry(request.user, 'ADD', f'Товар "{product.name}" (кол-во: {quantity}) добавлен в корзину №{cart.number} пользователем {request.user.username} через сканирование UUID')
        messages.success(request, f'Товар "{product.name}" добавлен в корзину №{cart.number}.')
        return redirect('cart_add_item', cart_id=cart.id)

    return redirect('products')

##################
### STATISTICS ###
##################

@login_required
def stats(request):
    sales = Sale.objects.filter(owner=request.user).prefetch_related('items__product').order_by('-date')
    today = timezone.now()

    daily_sales = sales.filter(date__date=today)
    weekly_sales = sales.filter(date__gte=today - timedelta(days=7))
    monthly_sales = sales.filter(date__gte=today - timedelta(days=30))

    daily_revenue = sum(item.actual_price_total for sale in daily_sales for item in sale.items.all())
    weekly_revenue = sum(item.actual_price_total for sale in weekly_sales for item in sale.items.all())
    monthly_revenue = sum(item.actual_price_total for sale in monthly_sales for item in sale.items.all())
    total_revenue = sum(item.actual_price_total for sale in sales for item in sale.items.all())

    total_sales_count = sales.count()
    total_amounts = [sum(item.actual_price_total for item in sale.items.all()) for sale in sales]
    average_check = sum(total_amounts) / len(total_amounts) if total_amounts else 0

    top_product_by_quantity = SaleItem.objects.filter(sale__owner=request.user).values('product__name').annotate(total_quantity=Sum('quantity')).order_by('-total_quantity').first()
    top_product_by_revenue = SaleItem.objects.filter(sale__owner=request.user).values('product__name').annotate(total_revenue=Sum('actual_price_total')).order_by('-total_revenue').first()

    category_stats = SaleItem.objects.filter(sale__owner=request.user).values('product__category__name').annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('actual_price_total')
    ).order_by('-total_revenue')

    subcategory_stats = SaleItem.objects.filter(sale__owner=request.user).values('product__subcategory__name').annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('actual_price_total')
    ).order_by('-total_revenue')

    warehouse_stats = SaleItem.objects.filter(sale__owner=request.user).values('product__warehouse__name').annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('actual_price_total')
    ).order_by('-total_revenue')

    daily_sales_last_week = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        day_sales = sales.filter(date__gte=day_start, date__lt=day_end)
        day_revenue = sum(item.actual_price_total for sale in day_sales for item in sale.items.all())
        daily_sales_last_week.append({
            'date': day_start.strftime('%Y-%m-%d'),
            'revenue': day_revenue
        })

    user_settings, created = UserSettings.objects.get_or_create(user=request.user)
    show_cost_price = not user_settings.hide_cost_price
    total_profit = daily_profit = weekly_profit = monthly_profit = None

    if show_cost_price:
        total_cost = sum(item.quantity * (item.product.cost_price or 0) for sale in sales for item in sale.items.all())
        total_profit = total_revenue - total_cost if total_cost is not None else total_revenue

        daily_cost = sum(item.quantity * (item.product.cost_price or 0) for sale in daily_sales for item in sale.items.all())
        daily_profit = daily_revenue - daily_cost if daily_cost is not None else daily_revenue

        weekly_cost = sum(item.quantity * (item.product.cost_price or 0) for sale in weekly_sales for item in sale.items.all())
        weekly_profit = weekly_revenue - weekly_cost if weekly_cost is not None else weekly_revenue

        monthly_cost = sum(item.quantity * (item.product.cost_price or 0) for sale in monthly_sales for item in sale.items.all())
        monthly_profit = monthly_revenue - monthly_cost if monthly_cost is not None else monthly_revenue

    return render(request, 'stats.html', {
        'daily_revenue': daily_revenue,
        'weekly_revenue': weekly_revenue,
        'monthly_revenue': monthly_revenue,
        'total_revenue': total_revenue,
        'total_sales_count': total_sales_count,
        'average_check': average_check,
        'top_product_by_quantity': top_product_by_quantity,
        'top_product_by_revenue': top_product_by_revenue,
        'category_stats': category_stats,
        'subcategory_stats': subcategory_stats,
        'warehouse_stats': warehouse_stats,
        'daily_sales_last_week': daily_sales_last_week,
        'show_cost_price': show_cost_price,
        'total_profit': total_profit,
        'daily_profit': daily_profit,
        'weekly_profit': weekly_profit,
        'monthly_profit': monthly_profit,
    })

################
### CATEGORY ###
################

@login_required
def category_manage(request):
    query = request.GET.get('q', '')
    sort_by = request.GET.get('sort_by', '')

    categories = Category.objects.filter(owner=request.user)
    subcategories = Subcategory.objects.filter(owner=request.user)

    if query:
        categories = categories.filter(name__icontains=query)
        subcategories = subcategories.filter(name__icontains=query)

    # Ensure consistent ordering
    allowed_sort_fields = ['name', '-name']
    if sort_by in allowed_sort_fields:
        categories = categories.order_by(sort_by)
        subcategories = subcategories.order_by(sort_by)
    else:
        categories = categories.order_by('name')  # Default ordering
        subcategories = subcategories.order_by('name')

    category_form = CategoryForm(user=request.user)
    subcategory_form = SubcategoryForm(user=request.user)

    if request.method == 'POST':
        if 'add_category' in request.POST:
            category_form = CategoryForm(request.POST, user=request.user)
            if category_form.is_valid():
                category = category_form.save(commit=False)
                category.owner = request.user
                category.save()
                create_log_entry(request.user, 'ADD', f'Модель "{category.name}" добавлена пользователем {request.user.username}')
                messages.success(request, 'Модель добавлена.')
                return redirect('category_manage')
            else:
                messages.error(request, 'Ошибка при добавлении модели.')
        elif 'add_subcategory' in request.POST:
            subcategory_form = SubcategoryForm(request.POST, user=request.user)
            if subcategory_form.is_valid():
                subcategory = subcategory_form.save(commit=False)
                subcategory.owner = request.user
                subcategory.save()
                create_log_entry(request.user, 'ADD', f'Цвет "{subcategory.name}" добавлен пользователем {request.user.username}')
                messages.success(request, 'Цвет добавлен.')
                return redirect('category_manage')
            else:
                messages.error(request, 'Ошибка при добавлении цвета.')

    return render(request, 'categories.html', {
        'categories': categories,
        'subcategories': subcategories,
        'category_form': category_form,
        'subcategory_form': subcategory_form,
        'query': query,
        'sort_by': sort_by,
    })

@login_required
def category_edit(request, category_id):
    category = get_object_or_404(Category, id=category_id, owner=request.user)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category, user=request.user)
        if form.is_valid():
            old_name = category.name
            category = form.save()
            create_log_entry(request.user, 'UPDATE', f'Модель "{old_name}" обновлена на "{category.name}" пользователем {request.user.username}')
            messages.success(request, 'Модель обновлена.')
            return redirect('category_manage')
        else:
            messages.error(request, 'Ошибка при обновлении модели.')
    else:
        form = CategoryForm(instance=category, user=request.user)
    return render(request, 'category_form.html', {'form': form, 'category': category})

@login_required
def category_delete(request, category_id):
    category = get_object_or_404(Category, id=category_id, owner=request.user)
    if request.method == 'POST':
        related_products = Product.objects.filter(category=category, owner=request.user)
        if related_products.exists():
            messages.error(request, f'Нельзя удалить модель "{category.name}", так как с ней связаны товары.')
            return redirect('category_manage')

        category_name = category.name
        category.delete()
        create_log_entry(request.user, 'DELETE', f'Модель "{category_name}" удалена пользователем {request.user.username}')
        messages.success(request, f'Модель "{category_name}" удалена.')
    return redirect('category_manage')

####################
### SUBCATEGORY ###
####################

@login_required
def subcategory_edit(request, subcategory_id):
    subcategory = get_object_or_404(Subcategory, id=subcategory_id, owner=request.user)
    if request.method == 'POST':
        form = SubcategoryForm(request.POST, instance=subcategory, user=request.user)
        if form.is_valid():
            form.save()
            create_log_entry(request.user, 'UPDATE', f'Цвет "{subcategory.name}" обновлен пользователем {request.user.username}')
            messages.success(request, 'Цвет обновлен.')
            return redirect('category_manage')
    else:
        form = SubcategoryForm(instance=subcategory, user=request.user)
    return render(request, 'subcategory_form.html', {'form': form, 'subcategory': subcategory})

@login_required
def subcategory_delete(request, subcategory_id):
    subcategory = get_object_or_404(Subcategory, id=subcategory_id, owner=request.user)
    if request.method == 'POST':
        related_products = Product.objects.filter(subcategory=subcategory, owner=request.user)
        if related_products.exists():
            messages.error(request, f'Нельзя удалить цвет "{subcategory.name}", так как с ним связаны товары.')
            return redirect('category_manage')

        subcategory_name = subcategory.name
        subcategory.delete()
        create_log_entry(request.user, 'DELETE', f'Цвет "{subcategory_name}" удален пользователем {request.user.username}')
        messages.success(request, f'Цвет "{subcategory_name}" удален.')
    return redirect('category_manage')

############################
### ADMIN PANEL (manual) ###
############################

@user_passes_test(lambda u: u.is_superuser)
def admin_panel(request):
    if request.method == 'POST':
        if 'user_id' in request.POST:
            user_id = request.POST.get('user_id')
            action = request.POST.get('action')
            user = get_object_or_404(User, id=user_id)
            user_settings = get_object_or_404(UserSettings, user=user)

            if action == 'approve' and user_settings.is_pending:
                user.is_active = True
                user_settings.is_pending = False
                user_settings.save()
                user.save()
                create_log_entry(request.user, 'APPROVE', f'Регистрация пользователя {user.username} подтверждена администратором {request.user.username}')
                messages.success(request, f'Регистрация пользователя {user.username} подтверждена.')
            elif action == 'reject' and user_settings.is_pending:
                create_log_entry(request.user, 'REJECT', f'Регистрация пользователя {user.username} отклонена администратором {request.user.username}')
                user.delete()
                messages.success(request, f'Запрос на регистрацию пользователя {user.username} отклонён.')
            elif action == 'block' and not user_settings.is_pending:
                user.is_active = False
                user.save()
                create_log_entry(request.user, 'BLOCK', f'Пользователь {user.username} заблокирован администратором {request.user.username}')
                messages.success(request, f'Пользователь {user.username} заблокирован.')
            elif action == 'unblock' and not user_settings.is_pending:
                user.is_active = True
                user.save()
                create_log_entry(request.user, 'UNBLOCK', f'Пользователь {user.username} разблокирован администратором {request.user.username}')
                messages.success(request, f'Пользователь {user.username} разблокирован.')
            elif action == 'delete' and not user_settings.is_pending:
                create_log_entry(request.user, 'DELETE', f'Пользователь {user.username} удалён администратором {request.user.username}')
                user.delete()
                messages.success(request, f'Пользователь {user.username} удален.')
            return redirect('admin_panel')

    # Запросы на регистрацию (pending_users)
    pending_users = User.objects.filter(usersettings__is_pending=True)

    q_pending = request.GET.get('q_pending', '')
    pending_date_from = request.GET.get('pending_date_from', '')
    pending_date_to = request.GET.get('pending_date_to', '')
    pending_sort_by = request.GET.get('pending_sort_by', '')

    if q_pending:
        pending_users = pending_users.filter(
            Q(email__icontains=q_pending) | Q(first_name__icontains=q_pending)
        )

    if pending_date_from:
        try:
            pending_date_from = timezone.datetime.strptime(pending_date_from, '%Y-%m-%d')
            pending_users = pending_users.filter(date_joined__gte=pending_date_from)
        except ValueError:
            messages.error(request, 'Неверный формат даты "с" для запросов. Используйте YYYY-MM-DD.')
    if pending_date_to:
        try:
            pending_date_to = timezone.datetime.strptime(pending_date_to, '%Y-%m-%d')
            pending_date_to = pending_date_to + timedelta(days=1)
            pending_users = pending_users.filter(date_joined__lt=pending_date_to)
        except ValueError:
            messages.error(request, 'Неверный формат даты "по" для запросов. Используйте YYYY-MM-DD.')

    # Ensure consistent ordering
    pending_allowed_sort_fields = [
        'email', '-email',
        'first_name', '-first_name',
        'date_joined', '-date_joined',
    ]
    if pending_sort_by in pending_allowed_sort_fields:
        pending_users = pending_users.order_by(pending_sort_by)
    else:
        pending_users = pending_users.order_by('date_joined')  # Default ordering

    # Пагинация для pending_users
    paginator_pending = Paginator(pending_users, 10)  # 10 запросов на страницу
    page_number_pending = request.GET.get('page_pending', 1)
    try:
        pending_users_paginated = paginator_pending.page(page_number_pending)
    except PageNotAnInteger:
        pending_users_paginated = paginator_pending.page(1)
    except EmptyPage:
        pending_users_paginated = paginator_pending.page(paginator_pending.num_pages)

    # Активные пользователи (active_users)
    active_users = User.objects.filter(usersettings__is_pending=False).exclude(is_superuser=True)

    q_active = request.GET.get('q_active', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    status = request.GET.get('status', '')
    sort_by = request.GET.get('sort_by', '')

    if q_active:
        active_users = active_users.filter(
            Q(email__icontains=q_active) | Q(first_name__icontains=q_active)
        )

    if date_from:
        try:
            date_from = timezone.datetime.strptime(date_from, '%Y-%m-%d')
            active_users = active_users.filter(date_joined__gte=date_from)
        except ValueError:
            messages.error(request, 'Неверный формат даты "с". Используйте YYYY-MM-DD.')
    if date_to:
        try:
            date_to = timezone.datetime.strptime(date_to, '%Y-%m-%d')
            date_to = date_to + timedelta(days=1)
            active_users = active_users.filter(date_joined__lt=date_to)
        except ValueError:
            messages.error(request, 'Неверный формат даты "по". Используйте YYYY-MM-DD.')

    if status:
        if status == 'active':
            active_users = active_users.filter(is_active=True)
        elif status == 'blocked':
            active_users = active_users.filter(is_active=False)

    # Ensure consistent ordering
    allowed_sort_fields = [
        'email', '-email',
        'first_name', '-first_name',
        'date_joined', '-date_joined',
        'is_active', '-is_active',
    ]
    if sort_by in allowed_sort_fields:
        active_users = active_users.order_by(sort_by)
    else:
        active_users = active_users.order_by('date_joined')  # Default ordering

    # Пагинация для active_users
    paginator_active = Paginator(active_users, 10)  # 10 пользователей на страницу
    page_number_active = request.GET.get('page_active', 1)
    try:
        active_users_paginated = paginator_active.page(page_number_active)
    except PageNotAnInteger:
        active_users_paginated = paginator_active.page(1)
    except EmptyPage:
        active_users_paginated = paginator_active.page(paginator_active.num_pages)

    categories = Category.objects.all().order_by('name')
    total_products = Product.objects.count()
    total_warehouses = Warehouse.objects.count()

    return render(request, 'admin.html', {
        'pending_users': pending_users_paginated,
        'active_users': active_users_paginated,
        'q_pending': q_pending,
        'pending_date_from': pending_date_from,
        'pending_date_to': pending_date_to,
        'pending_sort_by': pending_sort_by,
        'q_active': q_active,
        'date_from': date_from,
        'date_to': date_to,
        'status': status,
        'sort_by': sort_by,
        'categories': categories,
        'total_products': total_products,
        'total_warehouses': total_warehouses,
    })

############
### LOGS ###
############

@login_required
def logs(request):
    # Определяем, является ли пользователь админом
    is_admin = request.user.is_superuser

    # Фильтруем логи: админ видит все, обычный пользователь — только свои
    if is_admin:
        logs = LogEntry.objects.all()
    else:
        logs = LogEntry.objects.filter(user=request.user)

    user_filter = request.GET.get('user', '')
    action_type = request.GET.get('action_type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    sort_by = request.GET.get('sort_by', '')

    if user_filter:
        if is_admin:
            logs = logs.filter(user__username__icontains=user_filter)
        else:
            logs = logs.filter(user=request.user)
    if action_type:
        logs = logs.filter(action_type=action_type)
    if date_from:
        try:
            # Парсим дату и делаем её осведомлённой
            date_from = timezone.datetime.strptime(date_from, '%Y-%m-%d')
            date_from = timezone.make_aware(date_from)  # Делаем datetime осведомлённым
            logs = logs.filter(timestamp__gte=date_from)
        except ValueError:
            messages.error(request, 'Неверный формат даты "с". Используйте YYYY-MM-DD.')
    if date_to:
        try:
            # Парсим дату и делаем её осведомлённой
            date_to = timezone.datetime.strptime(date_to, '%Y-%m-%d')
            date_to = timezone.make_aware(date_to)  # Делаем datetime осведомлённым
            date_to = date_to + timedelta(days=1)
            logs = logs.filter(timestamp__lt=date_to)
        except ValueError:
            messages.error(request, 'Неверный формат даты "по". Используйте YYYY-MM-DD.')

    # Ensure consistent ordering
    allowed_sort_fields = [
        'timestamp', '-timestamp',
        'user__username', '-user__username',
        'action_type', '-action_type',
    ]
    if sort_by in allowed_sort_fields:
        logs = logs.order_by(sort_by)
    else:
        logs = logs.order_by('-timestamp')  # Default ordering

    # Пагинация
    paginator = Paginator(logs, 20)  # 20 логов на страницу
    page_number = request.GET.get('page', 1)
    try:
        logs_paginated = paginator.page(page_number)
    except PageNotAnInteger:
        logs_paginated = paginator.page(1)
    except EmptyPage:
        logs_paginated = paginator.page(paginator.num_pages)

    # Передаём полный список кортежей ACTION_TYPES
    action_types = LogEntry.ACTION_TYPES

    # Список пользователей для фильтра (только для админов)
    users = User.objects.all() if is_admin else []

    return render(request, 'user_logs.html', {
        'logs': logs_paginated,
        'action_types': action_types,
        'user_filter': user_filter,
        'action_type': action_type,
        'date_from': date_from,
        'date_to': date_to,
        'sort_by': sort_by,
        'users': users,
        'is_admin': is_admin,
    })

@user_passes_test(lambda u: u.is_superuser)
def logs_filter(request):
    user_filter = request.GET.get('user', '')
    action_type = request.GET.get('action_type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    sort_by = request.GET.get('sort_by', '')

    logs = LogEntry.objects.all()

    if user_filter:
        logs = logs.filter(user__username__icontains=user_filter)
    if action_type:
        logs = logs.filter(action_type=action_type)
    if date_from:
        try:
            date_from = timezone.datetime.strptime(date_from, '%Y-%m-%d')
            logs = logs.filter(timestamp__gte=date_from)
        except ValueError:
            messages.error(request, 'Неверный формат даты "с". Используйте YYYY-MM-DD.')
    if date_to:
        try:
            date_to = timezone.datetime.strptime(date_to, '%Y-%m-%d')
            date_to = date_to + timedelta(days=1)
            logs = logs.filter(timestamp__lt=date_to)
        except ValueError:
            messages.error(request, 'Неверный формат даты "по". Используйте YYYY-MM-DD.')

    # Ensure consistent ordering
    allowed_sort_fields = [
        'timestamp', '-timestamp',
        'user__username', '-user__username',
        'action_type', '-action_type',
    ]
    if sort_by in allowed_sort_fields:
        logs = logs.order_by(sort_by)
    else:
        logs = logs.order_by('-timestamp')  # Default ordering

    # Пагинация
    paginator = Paginator(logs, 20)  # 20 логов на страницу
    page_number = request.GET.get('page', 1)
    try:
        logs_paginated = paginator.page(page_number)
    except PageNotAnInteger:
        logs_paginated = paginator.page(1)
    except EmptyPage:
        logs_paginated = paginator.page(paginator.num_pages)

    return render(request, 'user_logs.html', {
        'logs': logs_paginated,
    })