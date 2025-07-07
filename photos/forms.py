# photos/forms.py

from django import forms
from .models import Photo

class PhotoForm(forms.ModelForm):
    class Meta:
        model = Photo
        fields = ['title', 'image', 'description'] # El usuario se asigna en la vista
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
        labels = {
            'title': 'Título de la Foto',
            'image': 'Archivo de Imagen',
            'description': 'Descripción/Comentario',
        }