# inventory/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Product, Warehouse, Category, Subcategory, UserSettings, CartItem, SaleItem

class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Пароль")
    email = forms.EmailField(label="Электронная почта", required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'password']
        labels = {
            'username': 'Имя пользователя',
            'email': 'Электронная почта',
            'first_name': 'Имя',
            'password': 'Пароль',
        }

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Этот email уже используется.")
        return email

class LoginForm(forms.Form):
    username = forms.CharField(label="Имя пользователя")
    password = forms.CharField(widget=forms.PasswordInput, label="Пароль")

class UserChangeForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email', 'first_name']
        labels = {
            'email': 'Электронная почта',
            'first_name': 'Имя',
        }

class UserSettingsForm(forms.ModelForm):
    class Meta:
        model = UserSettings
        fields = ['hide_cost_price']
        labels = {
            'hide_cost_price': 'Скрыть себестоимость',
        }

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['category', 'subcategory', 'quantity', 'cost_price', 'selling_price', 'photo', 'warehouse']
        labels = {
            'category': 'Модель',
            'subcategory': 'Цвет',
            'quantity': 'Количество',
            'cost_price': 'Себестоимость',
            'selling_price': 'Цена продажи',
            'photo': 'Фото',
            'warehouse': 'Склад',
        }
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control', 'id': 'id_category'}),
            'subcategory': forms.Select(attrs={'class': 'form-control', 'id': 'id_subcategory'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'cost_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'selling_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'warehouse': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user  # Сохраняем user для проверки
        if user:
            self.fields['category'].queryset = Category.objects.filter(owner=user)
            self.fields['subcategory'].queryset = Subcategory.objects.filter(owner=user)

    def clean_cost_price(self):
        cost_price = self.cleaned_data.get('cost_price')
        if cost_price is not None and cost_price < 0:
            raise forms.ValidationError("Себестоимость не может быть отрицательной.")
        return cost_price

    def clean_selling_price(self):
        selling_price = self.cleaned_data['selling_price']
        if selling_price < 0:
            raise forms.ValidationError("Цена продажи не может быть отрицательной.")
        return selling_price

    def clean_subcategory(self):
        subcategory = self.cleaned_data.get('subcategory')
        if not subcategory:
            raise forms.ValidationError("Цвет обязателен для заполнения.")
        return subcategory

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')
        subcategory = cleaned_data.get('subcategory')
        warehouse = cleaned_data.get('warehouse')

        # Проверяем уникальность комбинации category, subcategory, warehouse и owner
        if category and subcategory and warehouse and self.user:
            existing_product = Product.objects.filter(
                category=category,
                subcategory=subcategory,
                warehouse=warehouse,
                owner=self.user
            )
            # Если это редактирование, исключаем текущий объект из проверки
            if self.instance and self.instance.pk:
                existing_product = existing_product.exclude(pk=self.instance.pk)

            if existing_product.exists():
                raise forms.ValidationError(
                    f"Товар с моделью '{category.name}', цветом '{subcategory.name}' и складом '{warehouse.name}' уже существует."
                )

        return cleaned_data

class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ['name']
        labels = {
            'name': 'Название',
        }

class CartItemForm(forms.ModelForm):
    actual_price = forms.DecimalField(decimal_places=2, required=False, label="Фактическая цена за единицу")

    class Meta:
        model = CartItem
        fields = ['product', 'quantity', 'actual_price']
        labels = {
            'product': 'Товар',
            'quantity': 'Количество',
        }
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'actual_price': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        if quantity <= 0:
            raise forms.ValidationError("Количество должно быть больше 0.")
        return quantity

    def clean_actual_price(self):
        actual_price = self.cleaned_data.get('actual_price')
        if actual_price is not None and actual_price < 0:
            raise forms.ValidationError("Фактическая цена не может быть отрицательной.")
        return actual_price

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']
        labels = {
            'name': 'Модель',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_name(self):
        name = self.cleaned_data['name']
        if self.user:
            existing_category = Category.objects.filter(name=name, owner=self.user)
            if self.instance and self.instance.pk:
                existing_category = existing_category.exclude(pk=self.instance.pk)
            if existing_category.exists():
                raise forms.ValidationError("Модель с таким названием уже существует.")
        return name

class SubcategoryForm(forms.ModelForm):
    class Meta:
        model = Subcategory
        fields = ['name']
        labels = {
            'name': 'Цвет',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_name(self):
        name = self.cleaned_data['name']
        if self.user:
            existing_subcategory = Subcategory.objects.filter(name=name, owner=self.user)
            if self.instance and self.instance.pk:
                existing_subcategory = existing_subcategory.exclude(pk=self.instance.pk)
            if existing_subcategory.exists():
                raise forms.ValidationError("Цвет с таким названием уже существует.")
        return name

class SaleItemForm(forms.ModelForm):
    actual_price = forms.DecimalField(required=False, decimal_places=2, max_digits=10, label="Фактическая цена за единицу")

    class Meta:
        model = SaleItem
        fields = ['product', 'quantity', 'actual_price']
        labels = {
            'product': 'Товар',
            'quantity': 'Количество',
        }

class ReturnForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, label="Количество для возврата")