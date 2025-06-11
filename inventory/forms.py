# inventory/forms.py

from django import forms
from .models import Feedback, RoomType, FurnitureType

class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['name', 'email', 'message']
        labels = {
            'name': 'Имя',
            'email': 'Электронная почта',
            'message': 'Сообщение',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        }

class ProductFilterForm(forms.Form):
    room_type = forms.ModelChoiceField(
        queryset=RoomType.objects.all(),
        required=False,
        label="Тип комнаты",
        empty_label="Все",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    furniture_type = forms.ModelChoiceField(
        queryset=FurnitureType.objects.all(),
        required=False,
        label="Тип мебели",
        empty_label="Все",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    min_price = forms.FloatField(
        required=False,
        label="Минимальная цена",
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    max_price = forms.FloatField(
        required=False,
        label="Максимальная цена",
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )