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
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control', 'id': 'id_category'}),
            'subcategory': forms.Select(attrs={'class': 'form-control', 'id': 'id_subcategory'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'cost_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'selling_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
            'warehouse': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.all()  # Только категории
        self.fields['subcategory'].queryset = Subcategory.objects.none()
        if 'category' in self.data:
            try:
                category_id = int(self.data.get('category'))
                self.fields['subcategory'].queryset = Subcategory.objects.filter(category_id=category_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.category:
            self.fields['subcategory'].queryset = Subcategory.objects.filter(category=self.instance.category)

class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ['name']

class SaleForm(forms.ModelForm):
    actual_price = forms.DecimalField(decimal_places=2, required=False, label="Фактическая цена за единицу")

    class Meta:
        model = Sale
        fields = ['quantity', 'actual_price']
        widgets = {
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'actual_price': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']

class SubcategoryForm(forms.ModelForm):
    class Meta:
        model = Subcategory
        fields = ['name', 'category']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.all()

    def clean_name(self):
        name = self.cleaned_data['name']
        if Category.objects.filter(name=name).exists():
            raise forms.ValidationError("Это имя уже используется для категории.")
        return name