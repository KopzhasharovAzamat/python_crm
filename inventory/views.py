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
from .forms import RegisterForm, LoginForm, UserChangeForm, UserSettingsForm, ProductForm, WarehouseForm, CartItemForm, SaleItemForm, ReturnForm, BrandForm, ModelForm, ModelSpecificationForm, ProductTypeForm
from .models import Product, Warehouse, Sale, SaleItem, Cart, CartItem, UserSettings, User, Return, LogEntry, CartComment, SaleComment, Brand, Model, ModelSpecification, ProductType
from django.http import JsonResponse

# Helper function to log actions
def create_log_entry(user, action_type, message):
    LogEntry.objects.create(owner=user, action_type=action_type, message=message)

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
            UserSettings.objects.create(owner=user, is_pending=True)
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
    user_settings, created = UserSettings.objects.get_or_create(owner=request.user)
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
    product_type = request.GET.get('product_type', '')
    specification = request.GET.get('specification', '')
    warehouse = request.GET.get('warehouse', '')
    min_quantity = request.GET.get('min_quantity', '')
    sort_by = request.GET.get('sort_by', '')

    products = Product.objects.filter(is_archived=False)

    if query:
        try:
            uuid_obj = uuid.UUID(query)
            products = products.filter(unique_id=query)
        except ValueError:
            products = products.filter(Q(name__icontains=query))
    if product_type:
        products = products.filter(product_type__name=product_type)
    if specification:
        products = products.filter(specifications__id=specification)
    if warehouse:
        products = products.filter(warehouse__name=warehouse)
    if min_quantity:
        products = products.filter(quantity__gte=min_quantity)

    if sort_by:
        allowed_sort_fields = [
            'name', '-name',
            'product_type__name', '-product_type__name',
            'selling_price', '-selling_price',
            'quantity', '-quantity',
            'warehouse__name', '-warehouse__name'
        ]
        if sort_by in allowed_sort_fields:
            products = products.order_by(sort_by)
        else:
            products = products.order_by('name')
    else:
        products = products.order_by('name')

    paginator = Paginator(products, 10)
    page_number = request.GET.get('page', 1)
    try:
        products_paginated = paginator.page(page_number)
    except PageNotAnInteger:
        products_paginated = paginator.page(1)
    except EmptyPage:
        products_paginated = paginator.page(paginator.num_pages)

    product_types = ProductType.objects.all()
    specifications = ModelSpecification.objects.all()
    warehouses = Warehouse.objects.all()
    low_stock_message = request.session.pop('low_stock', None)

    return render(request, 'products.html', {
        'products': products_paginated,
        'product_types': product_types,
        'specifications': specifications,
        'warehouses': warehouses,
        'low_stock_message': low_stock_message,
    })

@login_required
def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    user_settings, created = UserSettings.objects.get_or_create(owner=request.user)
    show_cost_price = not user_settings.hide_cost_price
    return render(request, 'product_detail.html', {
        'product': product,
        'show_cost_price': show_cost_price,
    })

@login_required
def product_add(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            create_log_entry(request.user, 'ADD', f'Товар "{product.name}" добавлен пользователем {request.user.username}')
            if product.quantity < 5:
                messages.warning(request, f"Товар {product.name} заканчивается (осталось {product.quantity})")
            return redirect('products')
        else:
            return render(request, 'product_form.html', {'form': form})
    else:
        form = ProductForm()
    return render(request, 'product_form.html', {'form': form})

@login_required
def product_edit(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            product = form.save()
            create_log_entry(request.user, 'UPDATE', f'Товар "{product.name}" обновлён пользователем {request.user.username}')
            if product.quantity < 5:
                messages.warning(request, f"Товар {product.name} заканчивается (осталось {product.quantity})")
            return redirect('products')
    else:
        form = ProductForm(instance=product)
    return render(request, 'product_form.html', {'form': form})

@login_required
def product_delete(request, product_id):
    product = get_object_or_404(Product, id=product_id)
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
            product = Product.objects.get(id=product_id)
            return JsonResponse({
                'id': product.id,
                'name': product.name,
                'product_type': product.product_type.name if product.product_type else '',
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
    products = Product.objects.filter(is_archived=True).order_by('name')
    paginator = Paginator(products, 10)
    page_number = request.GET.get('page', 1)
    try:
        products_paginated = paginator.page(page_number)
    except PageNotAnInteger:
        products_paginated = paginator.page(1)
    except EmptyPage:
        products_paginated = paginator.page(paginator.num_pages)
    return render(request, 'archived_products.html', {'products': products_paginated})

@login_required
def product_archive(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        product.is_archived = True
        product.save()
        create_log_entry(request.user, 'UPDATE', f'Товар "{product.name}" архивирован пользователем {request.user.username}')
        messages.success(request, f'Товар "{product.name}" архивирован.')
    return redirect('products')

@login_required
def product_unarchive(request, product_id):
    product = get_object_or_404(Product, id=product_id)
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
                warehouse = form.save()
                create_log_entry(request.user, 'ADD', f'Склад "{warehouse.name}" добавлен пользователем {request.user.username}')
                messages.success(request, 'Склад добавлен.')
                return redirect('warehouses')
        elif 'warehouse_id' in request.POST and request.POST.get('action') == 'delete':
            warehouse = get_object_or_404(Warehouse, id=request.POST['warehouse_id'])
            warehouse_name = warehouse.name
            warehouse.delete()
            create_log_entry(request.user, 'DELETE', f'Склад "{warehouse_name}" удалён пользователем {request.user.username}')
            messages.success(request, 'Склад удален.')
            return redirect('warehouses')
    warehouses = Warehouse.objects.all().order_by('name')
    form = WarehouseForm()
    return render(request, 'warehouses.html', {'warehouses': warehouses, 'form': form})

@login_required
def warehouse_add(request):
    if request.method == 'POST':
        form = WarehouseForm(request.POST)
        if form.is_valid():
            warehouse = form.save()
            create_log_entry(request.user, 'ADD', f'Склад "{warehouse.name}" добавлен пользователем {request.user.username}')
            return redirect('warehouses')
    else:
        form = WarehouseForm()
    return render(request, 'warehouse_form.html', {'form': form})

@login_required
def warehouse_edit(request, warehouse_id):
    warehouse = get_object_or_404(Warehouse, id=warehouse_id)
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
    warehouse = get_object_or_404(Warehouse, id=warehouse_id)
    if request.method == 'POST':
        warehouse_name = warehouse.name
        warehouse.delete()
        create_log_entry(request.user, 'DELETE', f'Склад "{warehouse_name}" удалён пользователем {request.user.username}')
        messages.success(request, f'Склад "{warehouse_name}" удален.')
        return redirect('warehouses')
    return redirect('warehouses')


############
### BRAND and MODEL MANAGEMENT ###
############

@login_required
def brand_model_manage(request):
    query = request.GET.get('q', '')

    brands = Brand.objects.all()
    models = Model.objects.all()

    if query:
        brands = brands.filter(name__icontains=query)
        models = models.filter(Q(name__icontains=query) | Q(brand__name__icontains=query))

    brands = brands.order_by('name')
    models = models.order_by('name')

    brand_form = BrandForm()
    model_form = ModelForm()

    if request.method == 'POST':
        if 'add_brand' in request.POST:
            brand_form = BrandForm(request.POST)
            if brand_form.is_valid():
                brand = brand_form.save()
                create_log_entry(request.user, 'ADD',
                                 f'Марка "{brand.name}" добавлена пользователем {request.user.username}')
                messages.success(request, 'Марка добавлена.')
                return redirect('brand_model_manage')
            else:
                messages.error(request, 'Ошибка при добавлении марки.')
        elif 'add_model' in request.POST:
            model_form = ModelForm(request.POST)
            if model_form.is_valid():
                model = model_form.save()
                create_log_entry(request.user, 'ADD',
                                 f'Модель "{model.name}" добавлена пользователем {request.user.username}')
                messages.success(request, 'Модель добавлена.')
                return redirect('brand_model_manage')
            else:
                messages.error(request, 'Ошибка при добавлении модели.')

    return render(request, 'brand_model_manage.html', {
        'brands': brands,
        'models': models,
        'brand_form': brand_form,
        'model_form': model_form,
        'query': query,
    })


@login_required
def brand_manage(request):
    query = request.GET.get('q', '')
    sort_by = request.GET.get('sort_by', '')

    brands = Brand.objects.all()
    if query:
        brands = brands.filter(name__icontains=query)
    if sort_by in ['name', '-name']:
        brands = brands.order_by(sort_by)
    else:
        brands = brands.order_by('name')

    brand_form = BrandForm()
    if request.method == 'POST':
        brand_form = BrandForm(request.POST)
        if brand_form.is_valid():
            brand = brand_form.save()
            create_log_entry(request.user, 'ADD',
                             f'Марка "{brand.name}" добавлена пользователем {request.user.username}')
            messages.success(request, 'Марка добавлена.')
            return redirect('brand_model_manage')
        else:
            messages.error(request, 'Ошибка при добавлении марки.')

    return render(request, 'brands.html', {
        'brands': brands,
        'brand_form': brand_form,
        'query': query,
        'sort_by': sort_by,
    })


@login_required
def brand_edit(request, brand_id):
    brand = get_object_or_404(Brand, id=brand_id)
    if request.method == 'POST':
        form = BrandForm(request.POST, instance=brand)
        if form.is_valid():
            old_name = brand.name
            brand = form.save()
            create_log_entry(request.user, 'UPDATE',
                             f'Марка "{old_name}" обновлена на "{brand.name}" пользователем {request.user.username}')
            messages.success(request, 'Марка обновлена.')
            return redirect('brand_model_manage')
        else:
            messages.error(request, 'Ошибка при обновлении марки.')
    else:
        form = BrandForm(instance=brand)
    return render(request, 'brand_model_form.html', {'form': form})


@login_required
def brand_delete(request, brand_id):
    brand = get_object_or_404(Brand, id=brand_id)
    if request.method == 'POST':
        related_models = Model.objects.filter(brand=brand)
        if related_models.exists():
            messages.error(request, f'Нельзя удалить марку "{brand.name}", так как с ней связаны модели.')
            return redirect('brand_model_manage')
        brand_name = brand.name
        brand.delete()
        create_log_entry(request.user, 'DELETE', f'Марка "{brand_name}" удалена')
        messages.success(request, f'Марка "{brand_name}" удалена.')
    return redirect('brand_model_manage')


############
### MODEL ###
############

@login_required
def model_manage(request):
    query = request.GET.get('q', '')
    sort_by = request.GET.get('sort_by', '')

    models = Model.objects.all()
    if query:
        models = models.filter(Q(name__icontains=query) | Q(brand__name__icontains=query))
    if sort_by in ['name', '-name', 'brand__name', '-brand__name']:
        models = models.order_by(sort_by)
    else:
        models = models.order_by('name')

    model_form = ModelForm()
    if request.method == 'POST':
        model_form = ModelForm(request.POST)
        if model_form.is_valid():
            model = model_form.save()
            create_log_entry(request.user, 'ADD',
                             f'Модель "{model.name}" добавлена пользователем {request.user.username}')
            messages.success(request, 'Модель добавлена.')
            return redirect('brand_model_manage')
        else:
            messages.error(request, 'Ошибка при добавлении модели.')

    return render(request, 'brands.html', {
        'models': models,
        'model_form': model_form,
        'query': query,
        'sort_by': sort_by,
    })


@login_required
def model_edit(request, model_id):
    model = get_object_or_404(Model, id=model_id)
    if request.method == 'POST':
        form = ModelForm(request.POST, instance=model)
        if form.is_valid():
            old_name = model.name
            model = form.save()
            create_log_entry(request.user, 'UPDATE',
                             f'Модель "{old_name}" обновлена на "{model.name}" пользователем {request.user.username}')
            messages.success(request, 'Модель обновлена.')
            return redirect('brand_model_manage')
        else:
            messages.error(request, 'Ошибка при обновлении модели.')
    else:
        form = ModelForm(instance=model)
    return render(request, 'brand_model_form.html', {'form': form})


@login_required
def model_delete(request, model_id):
    model = get_object_or_404(Model, id=model_id)
    if request.method == 'POST':
        related_specifications = ModelSpecification.objects.filter(model=model)
        if related_specifications.exists():
            messages.error(request, f'Нельзя удалить модель "{model.name}", так как с ней связаны спецификации.')
            return redirect('brand_model_manage')
        model_name = model.name
        model.delete()
        create_log_entry(request.user, 'DELETE', f'Модель "{model_name}" удалена пользователем {request.user.username}')
        messages.success(request, f'Модель "{model_name}" удалена.')
    return redirect('brand_model_manage')

######################
### SPECIFICATION ###
######################

@login_required
def specification_manage(request):
    query = request.GET.get('q', '')
    sort_by = request.GET.get('sort_by', '')

    specifications = ModelSpecification.objects.all()
    if query:
        specifications = specifications.filter(Q(engine_code__icontains=query) | Q(model__name__icontains=query))
    if sort_by in ['model__name', '-model__name', 'engine_code', '-engine_code']:
        specifications = specifications.order_by(sort_by)
    else:
        specifications = specifications.order_by('model__name')

    specification_form = ModelSpecificationForm()
    if request.method == 'POST':
        specification_form = ModelSpecificationForm(request.POST)
        if specification_form.is_valid():
            specification = specification_form.save()
            create_log_entry(request.user, 'ADD', f'Спецификация для модели "{specification.model.name}" добавлена пользователем {request.user.username}')
            messages.success(request, 'Спецификация добавлена.')
            return redirect('brand_manage')
        else:
            messages.error(request, 'Ошибка при добавлении спецификации.')

    return render(request, 'brands.html', {
        'specifications': specifications,
        'specification_form': specification_form,
        'query': query,
        'sort_by': sort_by,
    })

@login_required
def specification_edit(request, specification_id):
    specification = get_object_or_404(ModelSpecification, id=specification_id)
    if request.method == 'POST':
        form = ModelSpecificationForm(request.POST, instance=specification)
        if form.is_valid():
            specification = form.save()
            create_log_entry(request.user, 'UPDATE', f'Спецификация для модели "{specification.model.name}" обновлена пользователем {request.user.username}')
            messages.success(request, 'Спецификация обновлена.')
            return redirect('brand_manage')
        else:
            messages.error(request, 'Ошибка при обновлении спецификации.')
    else:
        form = ModelSpecificationForm(instance=specification)
    return render(request, 'specification_form.html', {'form': form, 'specification': specification})

@login_required
def specification_delete(request, specification_id):
    specification = get_object_or_404(ModelSpecification, id=specification_id)
    if request.method == 'POST':
        related_products = Product.objects.filter(specifications=specification)
        if related_products.exists():
            messages.error(request, f'Нельзя удалить спецификацию для модели "{specification.model.name}", так как с ней связаны товары.')
            return redirect('brand_manage')
        specification_model = specification.model.name
        specification.delete()
        create_log_entry(request.user, 'DELETE', f'Спецификация для модели "{specification_model}" удалена пользователем {request.user.username}')
        messages.success(request, f'Спецификация для модели "{specification_model}" удалена.')
    return redirect('brand_manage')

###################
### PRODUCT TYPE ###
###################

@login_required
def product_type_manage(request):
    query = request.GET.get('q', '')
    sort_by = request.GET.get('sort_by', '')

    product_types = ProductType.objects.all()
    if query:
        product_types = product_types.filter(name__icontains=query)
    if sort_by in ['name', '-name']:
        product_types = product_types.order_by(sort_by)
    else:
        product_types = product_types.order_by('name')

    product_type_form = ProductTypeForm()
    if request.method == 'POST':
        product_type_form = ProductTypeForm(request.POST)
        if product_type_form.is_valid():
            product_type = product_type_form.save()
            create_log_entry(request.user, 'ADD', f'Тип товара "{product_type.name}" добавлен пользователем {request.user.username}')
            messages.success(request, 'Тип товара добавлен.')
            return redirect('product_type_manage')
        else:
            messages.error(request, 'Ошибка при добавлении типа товара.')

    return render(request, 'product_types.html', {
        'product_types': product_types,
        'product_type_form': product_type_form,
        'query': query,
        'sort_by': sort_by,
    })

@login_required
def product_type_edit(request, product_type_id):
    product_type = get_object_or_404(ProductType, id=product_type_id)
    if request.method == 'POST':
        form = ProductTypeForm(request.POST, instance=product_type)
        if form.is_valid():
            old_name = product_type.name
            product_type = form.save()
            create_log_entry(request.user, 'UPDATE', f'Тип товара "{old_name}" обновлен на "{product_type.name}" пользователем {request.user.username}')
            messages.success(request, 'Тип товара обновлен.')
            return redirect('product_type_manage')
        else:
            messages.error(request, 'Ошибка при обновлении типа товара.')
    else:
        form = ProductTypeForm(instance=product_type)
    return render(request, 'product_type_form.html', {'form': form, 'product_type': product_type})

@login_required
def product_type_delete(request, product_type_id):
    product_type = get_object_or_404(ProductType, id=product_type_id)
    if request.method == 'POST':
        related_products = Product.objects.filter(product_type=product_type)
        if related_products.exists():
            messages.error(request, f'Нельзя удалить тип товара "{product_type.name}", так как с ним связаны товары.')
            return redirect('product_type_manage')
        product_type_name = product_type.name
        product_type.delete()
        create_log_entry(request.user, 'DELETE', f'Тип товара "{product_type_name}" удален пользователем {request.user.username}')
        messages.success(request, f'Тип товара "{product_type_name}" удален.')
    return redirect('product_type_manage')

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

    paginator = Paginator(sales, 10)
    page_number = request.GET.get('page', 1)
    try:
        sales_paginated = paginator.page(page_number)
    except PageNotAnInteger:
        sales_paginated = paginator.page(1)
    except EmptyPage:
        sales_paginated = paginator.page(paginator.num_pages)

    warehouses = Warehouse.objects.all().order_by('name')
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
    products = Product.objects.filter(is_archived=False).order_by('name')
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
    return render(request, 'return_item.html', {'sale': sale, 'sale_item': sale_item, 'form': form})

@login_required
def sale_comment_add(request, sale_id):
    sale = get_object_or_404(Sale, id=sale_id, owner=request.user)
    if request.method == 'POST':
        comment_text = request.POST.get('comment_text', '').strip()
        if comment_text:
            comment = SaleComment.objects.create(sale=sale, owner=request.user, text=comment_text)
            create_log_entry(request.user, 'ADD', f'Комментарий к продаже №{sale.number} добавлен пользователем {request.user.username}')
            messages.success(request, 'Комментарий добавлен.')
        else:
            messages.error(request, 'Комментарий не может быть пустым.')
    return redirect('sale_detail', sale_id=sale.id)

@login_required
def sale_comment_edit(request, sale_id, comment_id):
    sale = get_object_or_404(Sale, id=sale_id, owner=request.user)
    comment = get_object_or_404(SaleComment, id=comment_id, sale=sale, owner=request.user)
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
    comment = get_object_or_404(SaleComment, id=comment_id, sale=sale, owner=request.user)
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
    carts = Cart.objects.all().prefetch_related('items__product', 'comments')
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

    allowed_sort_fields = [
        'number', '-number',
        'created_at', '-created_at',
        'total_cost', '-total_cost'
    ]
    if sort_by in allowed_sort_fields:
        carts = carts.order_by(sort_by)
    else:
        carts = carts.order_by('-created_at')

    paginator = Paginator(carts, 10)
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
            cart = Cart.objects.create()
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
    cart = get_object_or_404(Cart, id=cart_id)
    products = Product.objects.filter(is_archived=False).order_by('name')

    form = CartItemForm()
    form.fields['product'].queryset = products

    if request.method == 'POST':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            try:
                data = json.loads(request.body)
                product_id = data.get('product_id')
                quantity = int(data.get('quantity', 1))
                actual_price = float(data.get('actual_price', 0))

                try:
                    product = Product.objects.get(id=product_id, is_archived=False)
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
            return render(request, 'cart_form.html', {'form': form, 'cart': cart, 'products': products})

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
    cart = get_object_or_404(Cart, id=cart_id)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
    product_name = cart_item.product.name
    cart_item.delete()
    create_log_entry(request.user, 'DELETE', f'Товар "{product_name}" удалён из корзины №{cart.number} пользователем {request.user.username}')
    messages.success(request, f'Товар "{product_name}" удалён из корзины.')
    return redirect('cart_add_item', cart_id=cart.id)

@login_required
def cart_confirm(request, cart_id):
    cart = get_object_or_404(Cart, id=cart_id)
    cart_items = cart.items.all()

    if not cart_items:
        messages.error(request, 'Корзина пуста. Добавьте товары перед подтверждением.')
        return redirect('cart_list')

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

    sale = Sale.objects.create(owner=request.user)
    for product_id, data in product_quantities.items():
        product = Product.objects.get(id=product_id)
        total_quantity = data['quantity']
        product.quantity -= total_quantity
        product.save()
        for item in data['items']:
            SaleItem.objects.create(
                sale=sale,
                product=product,
                quantity=item.quantity,
                base_price_total=item.base_price_total,
                actual_price_total=item.actual_price_total
            )

    comments = cart.comments.all()
    for comment in comments:
        SaleComment.objects.create(
            sale=sale,
            owner=request.user,
            text=comment.text,
            created_at=comment.created_at,
            updated_at=comment.updated_at
        )

    create_log_entry(request.user, 'SALE', f'Продажа №{sale.number} создана на основе корзины №{cart.number} пользователем {request.user.username}')
    cart.delete()
    messages.success(request, 'Продажа успешно завершена.')
    return redirect('sales_list')

@login_required
def cart_cancel(request, cart_id):
    cart = get_object_or_404(Cart, id=cart_id)
    cart.delete()
    create_log_entry(request.user, 'DELETE', f'Корзина №{cart.number} отменена пользователем {request.user.username}')
    messages.success(request, 'Корзина отменена.')
    return redirect('products')

@login_required
def cart_delete(request, cart_id):
    cart = get_object_or_404(Cart, id=cart_id)
    if request.method == 'POST':
        cart.delete()
        create_log_entry(request.user, 'DELETE', f'Корзина №{cart.number} удалена пользователем {request.user.username}')
        messages.success(request, f'Корзина удалена.')
        return redirect('cart_list')
    return redirect('cart_list')

@login_required
def cart_comment_add(request, cart_id):
    cart = get_object_or_404(Cart, id=cart_id)
    if request.method == 'POST':
        comment_text = request.POST.get('comment_text', '').strip()
        if comment_text:
            comment = CartComment.objects.create(cart=cart, owner=request.user, text=comment_text)
            create_log_entry(request.user, 'ADD', f'Комментарий к корзине №{cart.number} добавлен пользователем {request.user.username}')
            messages.success(request, 'Комментарий добавлен.')
        else:
            messages.error(request, 'Комментарий не может быть пустым.')
    return redirect('cart_add_item', cart_id=cart.id)

@login_required
def cart_comment_edit(request, cart_id, comment_id):
    cart = get_object_or_404(Cart, id=cart_id)
    comment = get_object_or_404(CartComment, id=comment_id, cart=cart, owner=request.user)
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
    cart = get_object_or_404(Cart, id=cart_id)
    comment = get_object_or_404(CartComment, id=comment_id, cart=cart, owner=request.user)
    if request.method == 'POST':
        comment.delete()
        create_log_entry(request.user, 'DELETE', f'Комментарий к корзине №{cart.number} удалён пользователем {request.user.username}')
        messages.success(request, 'Комментарий удалён.')
    return redirect('cart_add_item', cart_id=cart.id)

##############
### SEARCH ###
##############

@login_required
def get_product_by_uuid(request):
    if request.method == 'GET':
        unique_id = request.GET.get('unique_id')
        try:
            product = Product.objects.get(unique_id=unique_id, is_archived=False)
            return JsonResponse({
                'id': product.id,
                'name': product.name,
                'product_type': product.product_type.name if product.product_type else '',
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
        product_id = request.GET.get('id')
        try:
            product = Product.objects.get(id=product_id, is_archived=False)
            return JsonResponse({
                'id': product.id,
                'name': product.name,
                'product_type': product.product_type.name if product.product_type else '',
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
        product = Product.objects.get(unique_id=unique_id, is_archived=False)
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
            product = Product.objects.get(id=product_id, is_archived=False)
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
        cart = Cart.objects.create()
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

###############
### STATS ###
###############

@login_required
def stats(request):
    sales = Sale.objects.filter(owner=request.user)
    returns = Return.objects.filter(owner=request.user)
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    total_sales = sales.count()
    total_sales_amount = sales.aggregate(total=Sum('items__actual_price_total'))['total'] or 0
    total_returns = returns.count()
    total_returns_quantity = returns.aggregate(total=Sum('quantity'))['total'] or 0

    sales_by_day = {
        (today - timedelta(days=i)).strftime('%Y-%m-%d'): 0
        for i in range(7)
    }
    for sale in sales.filter(date__gte=week_ago):
        sale_date = sale.date.date().strftime('%Y-%m-%d')
        sales_by_day[sale_date] = sales_by_day.get(sale_date, 0) + sale.items.aggregate(total=Sum('actual_price_total'))['total'] or 0

    top_products = SaleItem.objects.filter(sale__owner=request.user).values('product__name').annotate(
        total_quantity=Sum('quantity'),
        total_amount=Sum('actual_price_total')
    ).order_by('-total_quantity')[:5]

    low_stock_products = Product.objects.filter(quantity__lt=5, is_archived=False).order_by('quantity')[:5]

    sales_by_month = {
        (today - timedelta(days=30)).strftime('%Y-%m'): 0
    }
    for sale in sales.filter(date__gte=month_ago):
        sale_month = sale.date.date().strftime('%Y-%m')
        sales_by_month[sale_month] = sales_by_month.get(sale_month, 0) + sale.items.aggregate(total=Sum('actual_price_total'))['total'] or 0

    return render(request, 'stats.html', {
        'total_sales': total_sales,
        'total_sales_amount': total_sales_amount,
        'total_returns': total_returns,
        'total_returns_quantity': total_returns_quantity,
        'sales_by_day': sales_by_day,
        'top_products': top_products,
        'low_stock_products': low_stock_products,
        'sales_by_month': sales_by_month,
    })

##############
### LOGS ###
##############

@login_required
def logs(request):
    logs = LogEntry.objects.filter(owner=request.user).order_by('-timestamp')
    action_type = request.GET.get('action_type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    search_query = request.GET.get('search_query', '')

    if action_type:
        logs = logs.filter(action_type=action_type)
    if date_from:
        try:
            logs = logs.filter(timestamp__gte=timezone.datetime.strptime(date_from, '%Y-%m-%d'))
        except ValueError:
            messages.error(request, 'Неверный формат даты "с". Используйте YYYY-MM-DD.')
    if date_to:
        try:
            date_to = timezone.datetime.strptime(date_to, '%Y-%m-%d')
            date_to = date_to + timedelta(days=1)
            logs = logs.filter(timestamp__lt=date_to)
        except ValueError:
            messages.error(request, 'Неверный формат даты "по". Используйте YYYY-MM-DD.')
    if search_query:
        logs = logs.filter(message__icontains=search_query)

    paginator = Paginator(logs, 10)
    page_number = request.GET.get('page', 1)
    try:
        logs_paginated = paginator.page(page_number)
    except PageNotAnInteger:
        logs_paginated = paginator.page(1)
    except EmptyPage:
        logs_paginated = paginator.page(paginator.num_pages)

    action_types = LogEntry.objects.filter(owner=request.user).values('action_type').distinct()
    return render(request, 'logs.html', {
        'logs': logs_paginated,
        'action_type': action_type,
        'date_from': date_from,
        'date_to': date_to,
        'search_query': search_query,
        'action_types': action_types,
    })

###################
### ADMIN PANEL ###
###################

@user_passes_test(lambda u: u.is_superuser)
@login_required
def admin_panel(request):
    # Фильтры для ожидающих пользователей
    q_pending = request.GET.get('q_pending', '')
    pending_date_from = request.GET.get('pending_date_from', '')
    pending_date_to = request.GET.get('pending_date_to', '')

    pending_users = UserSettings.objects.filter(is_pending=True).select_related('owner')

    if q_pending:
        pending_users = pending_users.filter(
            Q(owner__email__icontains=q_pending) | Q(owner__first_name__icontains=q_pending) | Q(
                owner__username__icontains=q_pending)
        )

    if pending_date_from:
        try:
            pending_date_from = datetime.strptime(pending_date_from, '%Y-%m-%d')
            pending_users = pending_users.filter(owner__date_joined__gte=pending_date_from)
        except ValueError:
            messages.error(request, 'Неверный формат даты "с". Используйте YYYY-MM-DD.')

    if pending_date_to:
        try:
            pending_date_to = datetime.strptime(pending_date_to, '%Y-%m-%d') + timedelta(days=1)
            pending_users = pending_users.filter(owner__date_joined__lt=pending_date_to)
        except ValueError:
            messages.error(request, 'Неверный формат даты "по". Используйте YYYY-MM-DD.')

    # Сортировка по дате регистрации пользователя
    pending_users = pending_users.order_by('owner__date_joined')

    # Пагинация для ожидающих пользователей
    paginator_pending = Paginator(pending_users, 10)
    page_pending = request.GET.get('page_pending', 1)
    try:
        pending_users_paginated = paginator_pending.page(page_pending)
    except PageNotAnInteger:
        pending_users_paginated = paginator_pending.page(1)
    except EmptyPage:
        pending_users_paginated = paginator_pending.page(paginator_pending.num_pages)

    # Фильтры для активных пользователей
    q_active = request.GET.get('q_active', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    active_users = User.objects.filter(usersettings__is_pending=False).select_related('usersettings')

    if q_active:
        active_users = active_users.filter(
            Q(email__icontains=q_active) | Q(first_name__icontains=q_active) | Q(username__icontains=q_active)
        )

    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d')
            active_users = active_users.filter(date_joined__gte=date_from)
        except ValueError:
            messages.error(request, 'Неверный формат даты "с". Используйте YYYY-MM-DD.')

    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            active_users = active_users.filter(date_joined__lt=date_to)
        except ValueError:
            messages.error(request, 'Неверный формат даты "по". Используйте YYYY-MM-DD.')

    # Пагинация для активных пользователей
    paginator_active = Paginator(active_users, 10)
    page_active = request.GET.get('page_active', 1)
    try:
        active_users_paginated = paginator_active.page(page_active)
    except PageNotAnInteger:
        active_users_paginated = paginator_active.page(1)
    except EmptyPage:
        active_users_paginated = paginator_active.page(paginator_active.num_pages)

    # Статистика
    total_products = Product.objects.count()
    total_warehouses = Warehouse.objects.count()

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')
        if not user_id or not action:
            messages.error(request, 'Неверные данные запроса.')
            return redirect('admin_panel')
        try:
            if action in ['approve', 'reject']:
                user_settings = get_object_or_404(UserSettings, owner__id=user_id, is_pending=True)
                if action == 'approve':
                    user_settings.owner.is_active = True
                    user_settings.owner.save()
                    user_settings.is_pending = False
                    user_settings.save()
                    create_log_entry(request.user, 'APPROVE',
                                     f'Пользователь {user_settings.owner.username} подтверждён администратором {request.user.username}')
                    messages.success(request, f'Пользователь {user_settings.owner.username} подтверждён.')
                elif action == 'reject':
                    username = user_settings.owner.username
                    user_settings.owner.delete()
                    create_log_entry(request.user, 'REJECT',
                                     f'Пользователь {username} отклонён администратором {request.user.username}')
                    messages.success(request, f'Пользователь {username} отклонён.')
            elif action in ['block', 'unblock', 'delete']:
                user = get_object_or_404(User, id=user_id)
                if action == 'block':
                    user.is_active = False
                    user.save()
                    create_log_entry(request.user, 'BLOCK',
                                     f'Пользователь {user.username} заблокирован администратором {request.user.username}')
                    messages.success(request, f'Пользователь {user.username} заблокирован.')
                elif action == 'unblock':
                    user.is_active = True
                    user.save()
                    create_log_entry(request.user, 'UNBLOCK',
                                     f'Пользователь {user.username} разблокирован администратором {request.user.username}')
                    messages.success(request, f'Пользователь {user.username} разблокирован.')
                elif action == 'delete':
                    username = user.username
                    user.delete()
                    create_log_entry(request.user, 'DELETE',
                                     f'Пользователь {username} удалён администратором {request.user.username}')
                    messages.success(request, f'Пользователь {username} удалён.')
            else:
                messages.error(request, 'Неверное действие.')
        except Exception as e:
            messages.error(request, f'Ошибка при обработке запроса: {str(e)}')
        return redirect('admin_panel')

    return render(request, 'admin.html', {
        'pending_users': pending_users_paginated,
        'active_users': active_users_paginated,
        'total_products': total_products,
        'total_warehouses': total_warehouses,
        'q_pending': q_pending,
        'pending_date_from': pending_date_from,
        'pending_date_to': pending_date_to,
        'q_active': q_active,
        'date_from': date_from,
        'date_to': date_to,
    })