from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import timedelta
from .forms import RegisterForm, LoginForm, ProductForm, WarehouseForm, SaleForm
from .models import Product, Warehouse, Sale, Category
from django.contrib import messages

def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Регистрация успешна! Пожалуйста, войдите.')
            return redirect('login')
        else:
            messages.error(request, 'Ошибка при регистрации. Проверьте данные.')
    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})

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
    return redirect('login')

@login_required
def product_list(request):
    query = request.GET.get('q', '')
    category = request.GET.get('category', '')
    products = Product.objects.filter(owner=request.user)
    if query:
        products = products.filter(Q(name__icontains=query) | Q(subcategory__icontains=query))
    if category:
        products = products.filter(category__name=category)
    categories = Category.objects.all()
    return render(request, 'products.html', {'products': products, 'categories': categories})

@login_required
def product_add(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.owner = request.user
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
    product.delete()
    return redirect('products')

@login_required
def warehouse_list(request):
    warehouses = Warehouse.objects.filter(owner=request.user)
    return render(request, 'warehouses.html', {'warehouses': warehouses})

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
def sale_create(request, product_id):
    product = get_object_or_404(Product, id=product_id, owner=request.user)
    if request.method == 'POST':
        form = SaleForm(request.POST)
        if form.is_valid():
            sale = form.save(commit=False)
            sale.product = product
            sale.owner = request.user
            sale.base_price_total = product.selling_price * sale.quantity
            sale.actual_price_total = form.cleaned_data['actual_price'] * sale.quantity if form.cleaned_data['actual_price'] else sale.base_price_total
            product.quantity -= sale.quantity
            product.save()
            sale.save()
            return redirect('products')
    else:
        form = SaleForm()
    return render(request, 'sale_form.html', {'form': form, 'product': product})

@login_required
def scan_product(request):
    unique_id = request.GET.get('code')
    try:
        product = Product.objects.get(unique_id=unique_id, owner=request.user)
        return render(request, 'product_info.html', {
            'product': product,
            'warehouse': product.warehouse,
        })
    except Product.DoesNotExist:
        return render(request, 'error.html', {'message': 'Товар не найден'})

@login_required
def stats(request):
    sales = Sale.objects.filter(owner=request.user)
    today = timezone.now()
    daily_revenue = sales.filter(date__date=today).aggregate(total=Sum('actual_price_total'))['total'] or 0
    weekly_revenue = sales.filter(date__gte=today - timedelta(days=7)).aggregate(total=Sum('actual_price_total'))['total'] or 0
    monthly_revenue = sales.filter(date__gte=today - timedelta(days=30)).aggregate(total=Sum('actual_price_total'))['total'] or 0
    top_product = sales.values('product__name').annotate(total=Sum('quantity')).order_by('-total').first()
    return render(request, 'stats.html', {
        'daily_revenue': daily_revenue,
        'weekly_revenue': weekly_revenue,
        'monthly_revenue': monthly_revenue,
        'top_product': top_product,
    })

@user_passes_test(lambda u: u.is_superuser)
def admin_panel(request):
    users = User.objects.all()
    categories = Category.objects.all()
    return render(request, 'admin.html', {'users': users, 'categories': categories})