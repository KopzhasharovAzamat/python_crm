# inventory/forms.py
from django import forms
from django.contrib.auth.models import User
from .models import Product, Warehouse, UserSettings, CartItem, SaleItem, Brand, Model, ModelSpecification, ProductType

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
        fields = ['name', 'product_type', 'specifications', 'quantity', 'cost_price', 'selling_price', 'photo', 'warehouse']
        labels = {
            'name': 'Название',
            'product_type': 'Тип товара',
            'specifications': 'Спецификации',
            'quantity': 'Количество',
            'cost_price': 'Себестоимость',
            'selling_price': 'Цена продажи',
            'photo': 'Фото',
            'warehouse': 'Склад',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'product_type': forms.Select(attrs={'class': 'form-control'}),
            'specifications': forms.SelectMultiple(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'cost_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'selling_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'warehouse': forms.Select(attrs={'class': 'form-control'}),
        }

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

    def clean(self):
        cleaned_data = super().clean()
        product_type = cleaned_data.get('product_type')
        specifications = cleaned_data.get('specifications')
        warehouse = cleaned_data.get('warehouse')
        name = cleaned_data.get('name')

        # Проверяем уникальность комбинации name, product_type, specifications, warehouse
        if product_type and specifications and warehouse and name:
            existing_product = Product.objects.filter(
                name=name,
                product_type=product_type,
                warehouse=warehouse
            ).filter(specifications__in=specifications).distinct()
            if self.instance and self.instance.pk:
                existing_product = existing_product.exclude(pk=self.instance.pk)
            if existing_product.exists():
                raise forms.ValidationError(
                    f"Товар с названием '{name}', типом '{product_type.name}', спецификациями и складом '{warehouse.name}' уже существует."
                )

        return cleaned_data

class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ['name']
        labels = {
            'name': 'Название',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
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

class BrandForm(forms.ModelForm):
    class Meta:
        model = Brand
        fields = ['name']
        labels = {
            'name': 'Марка',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }

class ModelForm(forms.ModelForm):
    class Meta:
        model = Model
        fields = ['name', 'brand']
        labels = {
            'name': 'Модель',
            'brand': 'Марка',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'brand': forms.Select(attrs={'class': 'form-control'}),
        }

class ModelSpecificationForm(forms.ModelForm):
    class Meta:
        model = ModelSpecification
        fields = ['model', 'engine_capacity', 'engine_code', 'horsepower', 'production_start', 'production_end']
        labels = {
            'model': 'Модель',
            'engine_capacity': 'Объем двигателя',
            'engine_code': 'Код двигателя',
            'horsepower': 'Лошадиные силы',
            'production_start': 'Начало производства',
            'production_end': 'Конец производства',
        }
        widgets = {
            'model': forms.Select(attrs={'class': 'form-control'}),
            'engine_capacity': forms.NumberInput(attrs={'class': 'form-control'}),
            'engine_code': forms.TextInput(attrs={'class': 'form-control'}),
            'horsepower': forms.NumberInput(attrs={'class': 'form-control'}),
            'production_start': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'production_end': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

class ProductTypeForm(forms.ModelForm):
    class Meta:
        model = ProductType
        fields = ['name']
        labels = {
            'name': 'Тип товара',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }

class SaleItemForm(forms.ModelForm):
    actual_price = forms.DecimalField(required=False, decimal_places=2, max_digits=10, label="Фактическая цена за единицу")

    class Meta:
        model = SaleItem
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

class ReturnForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, label="Количество для возврата")