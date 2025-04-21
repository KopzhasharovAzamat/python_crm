# inventory/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, Q
from django.http import HttpResponseForbidden
from django.utils import timezone
from datetime import timedelta
from django.contrib import messages
from .forms import RegisterForm, LoginForm, ProductForm, WarehouseForm, SaleForm, UserChangeForm, UserSettingsForm, CategoryForm, SubcategoryForm
from .models import Product, Warehouse, Sale, Category, Subcategory, UserSettings, User, LogEntry
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
            UserSettings.objects.create(user=user)  # Создаем настройки пользователя
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

    # Фильтрация
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

    # Сортировка
    if sort_by:
        # Разрешаем только определённые поля для сортировки
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
            # По умолчанию сортировка по названию
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
            product.request = request  # Для уведомлений
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
    # Получаем все продажи текущего пользователя
    sales = Sale.objects.filter(owner=request.user)

    # Фильтры
    product_name = request.GET.get('product_name', '')
    warehouse = request.GET.get('warehouse', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    min_amount = request.GET.get('min_amount', '')
    max_amount = request.GET.get('max_amount', '')
    min_quantity = request.GET.get('min_quantity', '')
    max_quantity = request.GET.get('max_quantity', '')
    sort_by = request.GET.get('sort_by', '')

    # Фильтрация по названию товара
    if product_name:
        sales = sales.filter(product__name__icontains=product_name)

    # Фильтрация по складу
    if warehouse:
        sales = sales.filter(product__warehouse__name=warehouse)

    # Фильтрация по дате
    if date_from:
        try:
            date_from = timezone.datetime.strptime(date_from, '%Y-%m-%d')
            sales = sales.filter(date__gte=date_from)
        except ValueError:
            messages.error(request, 'Неверный формат даты "с". Используйте YYYY-MM-DD.')
    if date_to:
        try:
            date_to = timezone.datetime.strptime(date_to, '%Y-%m-%d')
            # Добавляем 1 день, чтобы включить выбранный день
            date_to = date_to + timedelta(days=1)
            sales = sales.filter(date__lt=date_to)
        except ValueError:
            messages.error(request, 'Неверный формат даты "по". Используйте YYYY-MM-DD.')

    # Фильтрация по сумме
    if min_amount:
        try:
            min_amount = float(min_amount)
            sales = sales.filter(actual_price_total__gte=min_amount)
        except ValueError:
            messages.error(request, 'Минимальная сумма должна быть числом.')
    if max_amount:
        try:
            max_amount = float(max_amount)
            sales = sales.filter(actual_price_total__lte=max_amount)
        except ValueError:
            messages.error(request, 'Максимальная сумма должна быть числом.')

    # Фильтрация по количеству
    if min_quantity:
        try:
            min_quantity = int(min_quantity)
            sales = sales.filter(quantity__gte=min_quantity)
        except ValueError:
            messages.error(request, 'Минимальное количество должно быть целым числом.')
    if max_quantity:
        try:
            max_quantity = int(max_quantity)
            sales = sales.filter(quantity__lte=max_quantity)
        except ValueError:
            messages.error(request, 'Максимальное количество должно быть целым числом.')

    # Сортировка
    allowed_sort_fields = [
        'date', '-date',
        'product__name', '-product__name',
        'quantity', '-quantity',
        'product__warehouse__name', '-product__warehouse__name',
        'actual_price_total', '-actual_price_total'
    ]
    if sort_by in allowed_sort_fields:
        sales = sales.order_by(sort_by)
    else:
        # По умолчанию сортировка по дате (сначала новые)
        sales = sales.order_by('-date')

    # Получаем список складов для фильтра
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
    actual_price_per_unit = sale.actual_price_total / sale.quantity if sale.quantity > 0 else 0
    return render(request, 'sale_detail.html', {
        'sale': sale,
        'actual_price_per_unit': actual_price_per_unit
    })

@login_required
def sale_create(request, product_id):
    product = get_object_or_404(Product, id=product_id, owner=request.user)
    if request.method == 'POST':
        form = SaleForm(request.POST)
        if form.is_valid():
            sale = form.save(commit=False)
            sale.product = product
            sale.owner = request.user
            # Рассчитываем base_price_total как quantity * product.selling_price
            sale.base_price_total = sale.quantity * product.selling_price
            # Рассчитываем actual_price_total
            actual_price = form.cleaned_data['actual_price'] or product.selling_price
            sale.actual_price_total = sale.quantity * actual_price
            if sale.quantity <= product.quantity:
                product.quantity -= sale.quantity
                product.save()
                sale.save()
                LogEntry.objects.create(
                    user=request.user,
                    action_type='SALE',
                    message=f'Продажа {sale.quantity} ед. товара "{product.name}" пользователем {request.user.username}'
                )
                messages.success(request, f'Продажа товара "{product.name}" на {sale.quantity} шт. успешно завершена!')
                return redirect('products')
            else:
                form.add_error('quantity', 'Недостаточно товара на складе.')
    else:
        form = SaleForm(initial={'actual_price': product.selling_price})
    return render(request, 'sale_form.html', {'form': form, 'product': product})

############
### SCAN ###
############

@login_required
def scan_product(request):
    unique_id = request.GET.get('code')
    try:
        product = Product.objects.get(unique_id=unique_id, owner=request.user)
        return render(request, 'product_info.html', {
            'product': product,
            'warehouse': product.warehouse,
            'form': SaleForm()  # Форма для продажи
        })
    except Product.DoesNotExist:
        return render(request, 'error.html', {'message': 'Товар не найден'})

##################
### STATISTICS ###
##################

@login_required
def stats(request):
    sales = Sale.objects.filter(owner=request.user)
    today = timezone.now()
    daily_revenue = sales.filter(date__date=today).aggregate(total=Sum('actual_price_total'))['total'] or 0
    weekly_revenue = sales.filter(date__gte=today - timedelta(days=7)).aggregate(total=Sum('actual_price_total'))['total'] or 0
    monthly_revenue = sales.filter(date__gte=today - timedelta(days=30)).aggregate(total=Sum('actual_price_total'))['total'] or 0
    top_product = sales.values('product__name').annotate(total=Sum('quantity')).order_by('-total').first()
    category_stats = sales.values('product__category__name').annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('actual_price_total')
    )
    user_settings = UserSettings.objects.get(user=request.user)
    show_cost_price = not user_settings.hide_cost_price
    return render(request, 'stats.html', {
        'daily_revenue': daily_revenue,
        'weekly_revenue': weekly_revenue,
        'monthly_revenue': monthly_revenue,
        'top_product': top_product,
        'category_stats': category_stats,
        'show_cost_price': show_cost_price,
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
                subcategory_form = SubcategoryForm()  # Пустая форма для подкатегорий
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
                category_form = CategoryForm()  # Пустая форма для категорий
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

@user_passes_test(lambda u: u.is_superuser)
def admin_logs(request):
    logs = LogEntry.objects.all().order_by('-timestamp')
    return render(request, 'admin_logs.html', {'logs': logs})