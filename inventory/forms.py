# inventory/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Product, Warehouse, Sale, Category, Subcategory, UserSettings

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=100, required=True)
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'password1', 'password2']

class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)

class UserChangeForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email', 'first_name']

class UserSettingsForm(forms.ModelForm):
    class Meta:
        model = UserSettings
        fields = ['hide_cost_price']

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'category', 'subcategory', 'quantity', 'cost_price', 'selling_price', 'photo', 'warehouse']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'category' in self.data:
            try:
                category_id = int(self.data.get('category'))
                self.fields['subcategory'].queryset = Subcategory.objects.filter(category_id=category_id)
            except (ValueError, TypeError):
                self.fields['subcategory'].queryset = Subcategory.objects.none()
        elif self.instance.pk and self.instance.subcategory:
            self.fields['subcategory'].queryset = Subcategory.objects.filter(category=self.instance.category)
        else:
            self.fields['subcategory'].queryset = Subcategory.objects.none()

class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ['name']

class SaleForm(forms.ModelForm):
    actual_price = forms.DecimalField(decimal_places=2, required=False)
    class Meta:
        model = Sale
        fields = ['quantity', 'actual_price']

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']

class SubcategoryForm(forms.ModelForm):
    class Meta:
        model = Subcategory
        fields = ['name', 'category']