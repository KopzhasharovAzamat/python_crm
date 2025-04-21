# inventory/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, Q
from django.http import HttpResponseForbidden
from django.utils import timezone
from datetime import timedelta
from django.contrib import messages
import logging
from .forms import RegisterForm, LoginForm, ProductForm, WarehouseForm, SaleForm, UserChangeForm, UserSettingsForm, CategoryForm, SubcategoryForm
from .models import Product, Warehouse, Sale, Category, Subcategory, UserSettings, User
from django.http import JsonResponse

logger = logging.getLogger('inventory')

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
            user = form.save()
            UserSettings.objects.create(user=user)  # Создаем настройки пользователя
            logger.info(f'New user registered: {user.username}')
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
    min_quantity = request.GET.get('min_quantity', '')
    products = Product.objects.filter(owner=request.user)
    if query:
        products = products.filter(Q(name__icontains=query) | Q(subcategory__name__icontains=query))
    if category:
        products = products.filter(category__name=category)
    if min_quantity:
        products = products.filter(quantity__gte=min_quantity)
    categories = Category.objects.all()
    low_stock_message = request.session.pop('low_stock', None)
    return render(request, 'products.html', {
        'products': products,
        'categories': categories,
        'low_stock_message': low_stock_message
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
        messages.success(request, f'Товар "{product_name}" удален.')
        logger.info(f'Product "{product_name}" deleted by user {request.user.username}')
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
                messages.success(request, 'Склад добавлен.')
                return redirect('warehouses')
        elif 'warehouse_id' in request.POST and request.POST.get('action') == 'delete':
            warehouse = get_object_or_404(Warehouse, id=request.POST['warehouse_id'], owner=request.user)
            warehouse.delete()
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
        messages.success(request, f'Склад "{warehouse_name}" удален.')
        logger.info(f'Warehouse "{warehouse_name}" deleted by user {request.user.username}')
        return redirect('warehouses')
    return redirect('warehouses')

############
### SALE ###
############

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
                logger.info(f'Sale of {sale.quantity} {product.name} by {request.user.username}')
                messages.success(request, f'Продажа товара "{product.name}" на {sale.quantity} шт. успешно завершена!')
                return redirect('products')
            else:
                form.add_error('quantity', 'Недостаточно товара на складе.')
    else:
        form = SaleForm(initial={'actual_price': product.selling_price})
    return render(request, 'sale_form.html', {'form': form, 'product': product})

### SCAN ###

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
                category_form.save()
                logger.info(f'Category {category_form.cleaned_data["name"]} added by admin {request.user.username}')
                messages.success(request, 'Категория добавлена.')
                return redirect('category_manage')
            else:
                messages.error(request, 'Ошибка при добавлении категории.')
                subcategory_form = SubcategoryForm()  # Пустая форма для подкатегорий
        elif 'add_subcategory' in request.POST:
            subcategory_form = SubcategoryForm(request.POST)
            if subcategory_form.is_valid():
                subcategory_form.save()
                logger.info(f'Subcategory {subcategory_form.cleaned_data["name"]} added by admin {request.user.username}')
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
            messages.success(request, 'Категория обновлена.')
            logger.info(f'Category "{category.name}" updated by admin {request.user.username}')
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
        messages.success(request, f'Категория "{category_name}" удалена.')
        logger.info(f'Category "{category_name}" deleted by admin {request.user.username}')
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
            messages.success(request, 'Подкатегория обновлена.')
            logger.info(f'Subcategory "{subcategory.name}" updated by admin {request.user.username}')
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
        messages.success(request, f'Подкатегория "{subcategory_name}" удалена.')
        logger.info(f'Subcategory "{subcategory_name}" deleted by admin {request.user.username}')
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
            logger.info(f'User {user.username} blocked by admin {request.user.username}')
            messages.success(request, f'Пользователь {user.username} заблокирован.')
        elif action == 'delete':
            logger.info(f'User {user.username} deleted by admin {request.user.username}')
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