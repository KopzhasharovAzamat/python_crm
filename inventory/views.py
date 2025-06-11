# inventory/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect
from .models import Product, RoomType, FurnitureType, Review
from .forms import FeedbackForm, ProductFilterForm

def home(request):
    products = Product.objects.order_by('-rating')[:6]
    reviews = Review.objects.all()[:7]
    return render(request, 'home.html', {
        'products': products,
        'reviews': reviews
    })

def products_list(request):
    form = ProductFilterForm(request.GET or None)
    products = Product.objects.all()

    if form.is_valid():
        if form.cleaned_data['room_type']:
            products = products.filter(furniture_type__room_type=form.cleaned_data['room_type'])
        if form.cleaned_data['furniture_type']:
            products = products.filter(furniture_type=form.cleaned_data['furniture_type'])
        if form.cleaned_data['min_price']:
            products = products.filter(price__gte=form.cleaned_data['min_price'])
        if form.cleaned_data['max_price']:
            products = products.filter(price__lte=form.cleaned_data['max_price'])

    # Фильтрация по категориям
    gostinnaya_products = products.filter(furniture_type__room_type__name="Гостиная")
    kuhnya_products = products.filter(furniture_type__room_type__name="Кухня")
    spalnya_products = products.filter(furniture_type__room_type__name="Спальня")

    return render(request, 'products_list.html', {
        'products': products,
        'form': form,
        'gostinnaya_products': products,
        'kuhnya_products': products,
        'spalnya_products': products,
    })

def product_detail(request, product):
    product = get_object_or_404(Product, id=product_id)
    product.views += 1
    product.save()
    return render(request, 'product_detail.html', {'product': product})

def feedback(request):
    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('products_list')
    else:
        form = FeedbackForm()
    return render(request, 'feedback.html', {'form': form})

def order_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    message = f"Здравствуйте! Хочу заказать товар:\n{product.name}\nЦена: {product.price} ₽.\nПожалуйста, свяжитесь со мной для подтверждения заказа."
    whatsapp_url = f"https://wa.me/996709757873?text={encodeURIComponent(message)}"
    return HttpResponseRedirect(whatsapp_url)