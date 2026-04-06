from django import forms
from .models import Member

class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        # Incluimos solo los campos que existen en tu nuevo models.py
        fields = [
            'first_name', 
            'last_name_paterno', 
            'last_name_materno', 
            'apodo', 
            'dni', 
            'birth_date', 
            'death_date',  # Cambiado de fallecimiento_date a death_date
            'lugar_nacimiento', 
            'lugar_residencia',
            'ocupacion', 
            'email', 
            'telefono', 
            'biografia',
            'foto_principal', 
            'relationship', 
            'padre', 
            'madre', 
            'conyuge'
        ]
        
        # Widgets para mejorar la apariencia y funcionalidad (calendarios)
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'death_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'biografia': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name_paterno': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name_materno': forms.TextInput(attrs={'class': 'form-control'}),
            'dni': forms.TextInput(attrs={'class': 'form-control'}),
            'relationship': forms.Select(attrs={'class': 'form-control'}),
            'padre': forms.Select(attrs={'class': 'form-control'}),
            'madre': forms.Select(attrs={'class': 'form-control'}),
            'conyuge': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super(MemberForm, self).__init__(*args, **kwargs)
        # Opcional: Personalización de etiquetas si lo deseas
        self.fields['death_date'].label = "Fecha de Fallecimiento"
        self.fields['birth_date'].label = "Fecha de Nacimiento"