# inventory/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, Q, Count, Avg
from django.http import HttpResponseForbidden
from django.utils import timezone
from datetime import timedelta
from django.contrib import messages
from .forms import RegisterForm, LoginForm, ProductForm, WarehouseForm, UserChangeForm, UserSettingsForm, CategoryForm, \
    SubcategoryForm, CartItemForm, ReturnForm, SaleItemForm
from .models import Product, Warehouse, Sale, SaleItem, Cart, CartItem, Category, Subcategory, UserSettings, User, \
    LogEntry, Return
from django.http import JsonResponse

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
            if user:
                login(request, user)
                LogEntry.objects.create(
                    user=user,
                    action_type='LOGIN',
                    message=f'Пользователь {user.username} вошёл в систему'
                )
                messages.success(request, 'Вход выполнен успешно!')
                return redirect('products')
            else:
                messages.error(request, 'Неверный логин или пароль.')
        else:
            messages.error(request, 'Ошибка в форме. Проверьте данные.')
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    user = request.user
    logout(request)
    if user.is_authenticated:
        LogEntry.objects.create(
            user=user,
            action_type='LOGOUT',
            message=f'Пользователь {user.username} вышел из системы'
        )
    messages.success(request, 'Вы вышли из системы.')
    return redirect('login')

################
### REGISTER ###
################

def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserSettings.objects.create(user=user)
            LogEntry.objects.create(
                user=user,
                action_type='REGISTER',
                message=f'Новый пользователь {user.username} зарегистрирован'
            )
            messages.success(request, 'Регистрация успешна! Пожалуйста, войдите.')
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
            LogEntry.objects.create(
                user=request.user,
                action_type='UPDATE',
                message=f'Пользователь {request.user.username} обновил свой профиль'
            )
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

    products = Product.objects.filter(owner=request.user)

    if query:
        products = products.filter(Q(name__icontains=query) | Q(subcategory__name__icontains=query))
    if category:
        products = products.filter(category__name=category)
    if subcategory:
        products = products.filter(subcategory__name=subcategory)
    if warehouse:
        products = products.filter(warehouse__name=warehouse)
    if min_quantity:
        products = products.filter(quantity__gte=min_quantity)

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

    categories = Category.objects.all()
    subcategories = Subcategory.objects.all()
    warehouses = Warehouse.objects.filter(owner=request.user)
    low_stock_message = request.session.pop('low_stock', None)

    return render(request, 'products.html', {
        'products': products,
        'categories': categories,
        'subcategories': subcategories,
        'warehouses': warehouses,
        'low_stock_message': low_stock_message,
    })

@login_required
def product_add(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.owner = request.user
            product.request = request
            product.save()
            LogEntry.objects.create(
                user=request.user,
                action_type='ADD',
                message=f'Товар "{product.name}" добавлен пользователем {request.user.username}'
            )
            return redirect('products')
    else:
        form = ProductForm()
        form.fields['warehouse'].queryset = Warehouse.objects.filter(owner=request.user)
    return render(request, 'product_form.html', {'form': form})

@login_required
def product_edit(request, product_id):
    product = get_object_or_404(Product, id=product_id, owner=request.user)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            LogEntry.objects.create(
                user=request.user,
                action_type='UPDATE',
                message=f'Товар "{product.name}" обновлён пользователем {request.user.username}'
            )
            return redirect('products')
    else:
        form = ProductForm(instance=product)
        form.fields['warehouse'].queryset = Warehouse.objects.filter(owner=request.user)
    return render(request, 'product_form.html', {'form': form})

@login_required
def product_delete(request, product_id):
    product = get_object_or_404(Product, id=product_id, owner=request.user)
    if request.method == 'POST':
        product_name = product.name
        product.delete()
        LogEntry.objects.create(
            user=request.user,
            action_type='DELETE',
            message=f'Товар "{product_name}" удалён пользователем {request.user.username}'
        )
        messages.success(request, f'Товар "{product_name}" удален.')
    return redirect('products')

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
                LogEntry.objects.create(
                    user=request.user,
                    action_type='ADD',
                    message=f'Склад "{warehouse.name}" добавлен пользователем {request.user.username}'
                )
                messages.success(request, 'Склад добавлен.')
                return redirect('warehouses')
        elif 'warehouse_id' in request.POST and request.POST.get('action') == 'delete':
            warehouse = get_object_or_404(Warehouse, id=request.POST['warehouse_id'], owner=request.user)
            warehouse_name = warehouse.name
            warehouse.delete()
            LogEntry.objects.create(
                user=request.user,
                action_type='DELETE',
                message=f'Склад "{warehouse_name}" удалён пользователем {request.user.username}'
            )
            messages.success(request, 'Склад удален.')
            return redirect('warehouses')
    warehouses = Warehouse.objects.filter(owner=request.user)
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
            LogEntry.objects.create(
                user=request.user,
                action_type='ADD',
                message=f'Склад "{warehouse.name}" добавлен пользователем {request.user.username}'
            )
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
            LogEntry.objects.create(
                user=request.user,
                action_type='UPDATE',
                message=f'Склад "{warehouse.name}" обновлён пользователем {request.user.username}'
            )
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
        LogEntry.objects.create(
            user=request.user,
            action_type='DELETE',
            message=f'Склад "{warehouse_name}" удалён пользователем {request.user.username}'
        )
        messages.success(request, f'Склад "{warehouse_name}" удален.')
        return redirect('warehouses')
    return redirect('warehouses')

############
### SALE ###
############

@login_required
def sales_list(request):
    sales = Sale.objects.filter(owner=request.user).prefetch_related('items__product')

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
        sales = sales.order_by('-date')

    warehouses = Warehouse.objects.filter(owner=request.user)

    return render(request, 'sales_list.html', {
        'sales': sales,
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
    base_total, actual_total = sale.calculate_totals()
    return render(request, 'sale_detail.html', {
        'sale': sale,
        'items': items,
        'base_total': base_total,
        'actual_total': actual_total
    })

@login_required
def sale_edit(request, sale_id):
    sale = get_object_or_404(Sale, id=sale_id, owner=request.user)
    products = Product.objects.filter(owner=request.user)

    # Инициализируем форму для добавления нового товара в продажу
    form = SaleItemForm()
    form.fields['product'].queryset = products

    if request.method == 'POST':
        if 'add_item' in request.POST:
            form = SaleItemForm(request.POST)
            if form.is_valid():
                sale_item = form.save(commit=False)
                product = sale_item.product
                sale_item.sale = sale  # Привязываем к продаже, а не к корзине
                sale_item.base_price_total = sale_item.quantity * product.selling_price
                actual_price = form.cleaned_data['actual_price'] or product.selling_price
                sale_item.actual_price_total = sale_item.quantity * actual_price

                if sale_item.quantity <= product.quantity:
                    product.quantity -= sale_item.quantity  # Уменьшаем остаток
                    product.save()
                    sale_item.save()
                    LogEntry.objects.create(
                        user=request.user,
                        action_type='UPDATE',
                        message=f'Товар "{product.name}" (кол-во: {sale_item.quantity}) добавлен в продажу {sale.id} пользователем {request.user.username}'
                    )
                    messages.success(request, f'Товар "{product.name}" добавлен в продажу.')
                    return redirect('sale_edit', sale_id=sale.id)
                else:
                    messages.error(request, 'Недостаточно товара на складе.')
        elif 'delete_item' in request.POST:
            item_id = request.POST.get('item_id')
            sale_item = get_object_or_404(SaleItem, id=item_id, sale=sale)
            product = sale_item.product
            product.quantity += sale_item.quantity  # Возвращаем остаток на склад
            product.save()
            sale_item.delete()
            LogEntry.objects.create(
                user=request.user,
                action_type='UPDATE',
                message=f'Товар "{product.name}" (кол-во: {sale_item.quantity}) удалён из продажи {sale.id} пользователем {request.user.username}'
            )
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

            # Создаём запись о возврате
            return_record = Return.objects.create(
                sale=sale,
                sale_item=sale_item,
                quantity=return_quantity,
                owner=request.user
            )

            # Уменьшаем количество в SaleItem
            sale_item.quantity -= return_quantity
            if sale_item.quantity == 0:
                sale_item.delete()
            else:
                sale_item.base_price_total = sale_item.quantity * sale_item.product.selling_price
                sale_item.actual_price_total = sale_item.quantity * (sale_item.actual_price_total / (sale_item.quantity + return_quantity))
                sale_item.save()

            # Увеличиваем остаток на складе
            product = sale_item.product
            product.quantity += return_quantity
            product.save()

            # Логируем возврат
            LogEntry.objects.create(
                user=request.user,
                action_type='RETURN',
                message=f'Возврат {return_quantity} x "{product.name}" из продажи {sale.id} пользователем {request.user.username}'
            )
            messages.success(request, f'Возвращено {return_quantity} шт. товара "{product.name}".')
            return redirect('sale_detail', sale_id=sale.id)
    else:
        form = ReturnForm()

    return render(request, 'return_item.html', {
        'sale': sale,
        'sale_item': sale_item,
        'form': form
    })

############
### CART ###
############

@login_required
def cart_list(request):
    carts = Cart.objects.filter(owner=request.user).prefetch_related('items__product')
    return render(request, 'cart_list.html', {'carts': carts})


@login_required
def cart_create(request):
    if request.method == 'POST':
        cart = Cart.objects.create(owner=request.user)
        LogEntry.objects.create(
            user=request.user,
            action_type='ADD',
            message=f'Новая корзина {cart.id} создана пользователем {request.user.username}'
        )
        return redirect('cart_add_item', cart_id=cart.id)
    return render(request, 'cart_create.html')


@login_required
def cart_add_item(request, cart_id):
    cart = get_object_or_404(Cart, id=cart_id, owner=request.user)
    products = Product.objects.filter(owner=request.user)

    # Инициализируем form в начале, чтобы она всегда была определена
    form = CartItemForm()
    form.fields['product'].queryset = products
    scanned_product = None
    auto_open_modal = False  # Флаг для автоматического открытия модального окна

    if request.method == 'POST':
        if 'scan_code' in request.POST:
            unique_id = request.POST.get('unique_id')
            try:
                scanned_product = Product.objects.get(unique_id=unique_id, owner=request.user)
                auto_open_modal = True  # Открываем модальное окно автоматически
            except Product.DoesNotExist:
                messages.error(request, 'Товар с таким кодом не найден.')
                auto_open_modal = True  # Открываем модальное окно даже при ошибке

        elif 'add_scanned_item' in request.POST:
            form = CartItemForm(request.POST)
            if form.is_valid():
                cart_item = form.save(commit=False)
                cart_item.cart = cart
                product = cart_item.product
                cart_item.base_price_total = cart_item.quantity * product.selling_price
                actual_price = form.cleaned_data['actual_price'] or product.selling_price
                cart_item.actual_price_total = cart_item.quantity * actual_price

                if cart_item.quantity <= product.quantity:
                    cart_item.save()
                    messages.success(request, f'Товар "{product.name}" добавлен в корзину.')
                    return redirect('cart_add_item', cart_id=cart.id)
                else:
                    messages.error(request, 'Недостаточно товара на складе.')
                    auto_open_modal = True  # Открываем модальное окно при ошибке

        elif 'cancel_scan' in request.POST:
            # При отмене сканирования сбрасываем scanned_product
            return redirect('cart_add_item', cart_id=cart.id)

        else:
            form = CartItemForm(request.POST)
            if form.is_valid():
                cart_item = form.save(commit=False)
                cart_item.cart = cart
                product = cart_item.product
                cart_item.base_price_total = cart_item.quantity * product.selling_price
                actual_price = form.cleaned_data['actual_price'] or product.selling_price
                cart_item.actual_price_total = cart_item.quantity * actual_price

                if cart_item.quantity <= product.quantity:
                    cart_item.save()
                    messages.success(request, f'Товар "{product.name}" добавлен в корзину.')
                    return redirect('cart_add_item', cart_id=cart.id)
                else:
                    form.add_error('quantity', 'Недостаточно товара на складе.')

    return render(request, 'cart_form.html', {
        'form': form,
        'cart': cart,
        'products': products,
        'scanned_product': scanned_product,
        'auto_open_modal': auto_open_modal
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

    for item in cart_items:
        product = item.product
        if item.quantity > product.quantity:
            messages.error(request,
                           f'Недостаточно товара "{product.name}" на складе (осталось {product.quantity} шт.).')
            return redirect('cart_add_item', cart_id=cart.id)

    sale = Sale.objects.create(owner=request.user)
    for cart_item in cart_items:
        product = cart_item.product
        product.quantity -= cart_item.quantity
        product.save()
        SaleItem.objects.create(
            sale=sale,
            product=cart_item.product,
            quantity=cart_item.quantity,
            base_price_total=cart_item.base_price_total,
            actual_price_total=cart_item.actual_price_total
        )

    LogEntry.objects.create(
        user=request.user,
        action_type='SALE',
        message=f'Продажа {sale.id} на основе корзины {cart.id} завершена пользователем {request.user.username}'
    )

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
        LogEntry.objects.create(
            user=request.user,
            action_type='DELETE',
            message=f'Корзина {cart.id} удалена пользователем {request.user.username}'
        )
        messages.success(request, 'Корзина удалена.')
        return redirect('cart_list')
    return redirect('cart_list')

############
### SCAN ###
############

@login_required
def scan_product(request):
    unique_id = request.GET.get('code')
    try:
        product = Product.objects.get(unique_id=unique_id, owner=request.user)
        cart = Cart.objects.create(owner=request.user)
        LogEntry.objects.create(
            user=request.user,
            action_type='ADD',
            message=f'Новая корзина {cart.id} создана пользователем {request.user.username} через сканирование'
        )
        return redirect('cart_add_item', cart_id=cart.id)
    except Product.DoesNotExist:
        return render(request, 'error.html', {'message': 'Товар не найден'})

##################
### STATISTICS ###
##################

@login_required
def stats(request):
    sales = Sale.objects.filter(owner=request.user).prefetch_related('items__product')
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

    user_settings = UserSettings.objects.get(user=request.user)
    show_cost_price = not user_settings.hide_cost_price
    total_profit = None
    daily_profit = None
    weekly_profit = None
    monthly_profit = None

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

@user_passes_test(lambda u: u.is_superuser)
def category_manage(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("You do not have permission to access this page.")
    if request.method == 'POST':
        if 'add_category' in request.POST:
            category_form = CategoryForm(request.POST)
            if category_form.is_valid():
                category = category_form.save()
                LogEntry.objects.create(
                    user=request.user,
                    action_type='ADD',
                    message=f'Категория "{category.name}" добавлена администратором {request.user.username}'
                )
                messages.success(request, 'Категория добавлена.')
                return redirect('category_manage')
            else:
                messages.error(request, 'Ошибка при добавлении категории.')
                subcategory_form = SubcategoryForm()
        elif 'add_subcategory' in request.POST:
            subcategory_form = SubcategoryForm(request.POST)
            if subcategory_form.is_valid():
                subcategory = subcategory_form.save()
                LogEntry.objects.create(
                    user=request.user,
                    action_type='ADD',
                    message=f'Подкатегория "{subcategory.name}" добавлена администратором {request.user.username}'
                )
                messages.success(request, 'Подкатегория добавлена.')
                return redirect('category_manage')
            else:
                messages.error(request, 'Ошибка при добавлении подкатегории.')
                category_form = CategoryForm()
        else:
            category_form = CategoryForm()
            subcategory_form = SubcategoryForm()
    else:
        category_form = CategoryForm()
        subcategory_form = SubcategoryForm()
    categories = Category.objects.all()
    return render(request, 'category_manage.html', {
        'category_form': category_form,
        'subcategory_form': subcategory_form,
        'categories': categories,
    })

@user_passes_test(lambda u: u.is_superuser)
def category_edit(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            LogEntry.objects.create(
                user=request.user,
                action_type='UPDATE',
                message=f'Категория "{category.name}" обновлена администратором {request.user.username}'
            )
            messages.success(request, 'Категория обновлена.')
            return redirect('category_manage')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'category_form.html', {'form': form, 'category': category})

@user_passes_test(lambda u: u.is_superuser)
def category_delete(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if request.method == 'POST':
        category_name = category.name
        category.delete()
        LogEntry.objects.create(
            user=request.user,
            action_type='DELETE',
            message=f'Категория "{category_name}" удалена администратором {request.user.username}'
        )
        messages.success(request, f'Категория "{category_name}" удалена.')
    return redirect('category_manage')

####################
### SUBCATEGORY ###
####################

@login_required
def get_subcategories(request):
    category_id = request.GET.get('category_id')
    subcategories = Subcategory.objects.filter(category_id=category_id).values('id', 'name')
    return JsonResponse({'subcategories': list(subcategories)})

@user_passes_test(lambda u: u.is_superuser)
def subcategory_edit(request, subcategory_id):
    subcategory = get_object_or_404(Subcategory, id=subcategory_id)
    if request.method == 'POST':
        form = SubcategoryForm(request.POST, instance=subcategory)
        if form.is_valid():
            form.save()
            LogEntry.objects.create(
                user=request.user,
                action_type='UPDATE',
                message=f'Подкатегория "{subcategory.name}" обновлена администратором {request.user.username}'
            )
            messages.success(request, 'Подкатегория обновлена.')
            return redirect('category_manage')
    else:
        form = SubcategoryForm(instance=subcategory)
    return render(request, 'subcategory_form.html', {'form': form, 'subcategory': subcategory})

@user_passes_test(lambda u: u.is_superuser)
def subcategory_delete(request, subcategory_id):
    subcategory = get_object_or_404(Subcategory, id=subcategory_id)
    if request.method == 'POST':
        subcategory_name = subcategory.name
        subcategory.delete()
        LogEntry.objects.create(
            user=request.user,
            action_type='DELETE',
            message=f'Подкатегория "{subcategory_name}" удалена администратором {request.user.username}'
        )
        messages.success(request, f'Подкатегория "{subcategory_name}" удалена.')
    return redirect('category_manage')

############################
### ADMIN PANEL (manual) ###
############################

@user_passes_test(lambda u: u.is_superuser)
def admin_panel(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')
        user = User.objects.get(id=user_id)
        if action == 'block':
            user.is_active = False
            user.save()
            LogEntry.objects.create(
                user=request.user,
                action_type='BLOCK',
                message=f'Пользователь {user.username} заблокирован администратором {request.user.username}'
            )
            messages.success(request, f'Пользователь {user.username} заблокирован.')
        elif action == 'unblock':
            user.is_active = True
            user.save()
            LogEntry.objects.create(
                user=request.user,
                action_type='UNBLOCK',
                message=f'Пользователь {user.username} разблокирован администратором {request.user.username}'
            )
            messages.success(request, f'Пользователь {user.username} разблокирован.')
        elif action == 'delete':
            LogEntry.objects.create(
                user=request.user,
                action_type='DELETE',
                message=f'Пользователь {user.username} удалён администратором {request.user.username}'
            )
            user.delete()
            messages.success(request, f'Пользователь {user.username} удален.')
        return redirect('admin_panel')
    users = User.objects.all()
    categories = Category.objects.all()
    total_products = Product.objects.count()
    total_warehouses = Warehouse.objects.count()
    return render(request, 'admin.html', {
        'users': users,
        'categories': categories,
        'total_products': total_products,
        'total_warehouses': total_warehouses,
    })

############
### LOGS ###
############

@user_passes_test(lambda u: u.is_superuser)
def admin_logs(request):
    logs = LogEntry.objects.all().order_by('-timestamp')
    return render(request, 'admin_logs.html', {'logs': logs})

@login_required
def user_logs(request):
    # Получаем логи только для текущего пользователя
    logs = LogEntry.objects.filter(user=request.user).order_by('-timestamp')

    # Фильтры
    action_type = request.GET.get('action_type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

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

    # Получаем список типов действий для фильтра
    action_types = LogEntry.ACTION_TYPES

    return render(request, 'user_logs.html', {
        'logs': logs,
        'action_types': action_types,
        'action_type': action_type,
        'date_from': date_from,
        'date_to': date_to,
    })

@user_passes_test(lambda u: u.is_superuser)
def admin_logs(request):
    logs = LogEntry.objects.all().order_by('-timestamp')
    return render(request, 'admin_logs.html', {'logs': logs})