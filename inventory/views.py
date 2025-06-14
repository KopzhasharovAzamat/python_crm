# inventory/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login as auth_login, logout as auth_logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from .models import Design, PortfolioItem, Tariff, Review, Category
from .forms import ConsultationRequestForm, OrderForm, ReviewForm

def home(request):
    categories = Category.objects.all()
    portfolio_preview = PortfolioItem.objects.filter(show_on_main=True).select_related('design')[:9]
    reviews = Review.objects.order_by('-created_at')[:3]
    return render(request, 'home.html', {
        'categories': categories,
        'portfolio_preview': portfolio_preview,
        'reviews': reviews
    })

def portfolio(request):
    categories = Category.objects.all()
    items = PortfolioItem.objects.select_related('design').all()
    return render(request, 'portfolio.html', {'items': items, 'categories': categories, 'selected_category': None})

def portfolio_detail(request, pk):
    item = get_object_or_404(PortfolioItem, pk=pk)
    reviews = item.design.reviews.all()
    return render(request, 'portfolio_detail.html', {'item': item, 'reviews': reviews})

def services(request):
    tariffs = Tariff.objects.all()
    return render(request, 'services.html', {'tariffs': tariffs})

def consultation(request):
    if request.method == "POST":
        form = ConsultationRequestForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Ваша заявка отправлена!")
            return redirect('home')
    else:
        form = ConsultationRequestForm()
    return render(request, 'consultation.html', {'form': form})

@login_required
def order(request):
    if request.method == "POST":
        form = OrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.client = request.user
            order.save()
            messages.success(request, "Заказ успешно оформлен!")
            return redirect('home')
    else:
        form = OrderForm()
    return render(request, 'order.html', {'form': form})

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(request, "Регистрация успешна! Добро пожаловать!")
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})

def login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            messages.success(request, "Вы успешно вошли!")
            next_url = request.POST.get('next', '/')
            return redirect(next_url)
        else:
            messages.error(request, "Неверное имя пользователя или пароль.")
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})

def logout(request):
    auth_logout(request)
    messages.success(request, "Вы успешно вышли.")
    return redirect('login')

def reviews(request):
    all_reviews = Review.objects.order_by('-created_at')
    return render(request, 'reviews.html', {'reviews': all_reviews})

@login_required
def add_review(request, design_id):
    design = get_object_or_404(Design, pk=design_id)
    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            rev = form.save(commit=False)
            rev.design = design
            rev.user = request.user
            rev.save()
            messages.success(request, "Спасибо за ваш отзыв!")
            return redirect('portfolio_detail', pk=design.portfolioitem.pk)
    else:
        form = ReviewForm()
    return render(request, 'add_review.html', {'form': form, 'design': design})

def portfolio_by_category(request, category_id):
    categories = Category.objects.all()
    selected_category = get_object_or_404(Category, pk=category_id)
    items = PortfolioItem.objects.select_related('design').filter(design__category=selected_category)
    return render(request, 'portfolio.html', {'items': items, 'categories': categories, 'selected_category': selected_category})

def about(request):
    return render(request, 'about.html')

def contacts(request):
    return render(request, 'contacts.html')

def faq(request):
    return render(request, 'faq.html')

def designers(request):
    return render(request, 'designers.html')