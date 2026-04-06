from django import forms
from .models import Member

class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = '__all__' # O tu lista de campos actual
        widgets = {
            'birth_date': forms.DateInput(
                format='%Y-%m-%d', 
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'death_date': forms.DateInput(
                format='%Y-%m-%d', 
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            # Mantén tus otros widgets igual...
            'biografia': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Esto asegura que Django use el formato ISO al renderizar el valor existente
        if self.instance and self.instance.birth_date:
            self.initial['birth_date'] = self.instance.birth_date.strftime('%Y-%m-%d')
        if self.instance and self.instance.death_date:
            self.initial['death_date'] = self.instance.death_date.strftime('%Y-%m-%d')