from django import forms
from .models import Member

class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        # Asegúrate de que los 'fields' aquí coincidan exactamente
        # con los nombres de los campos en tu models.py.
        # Basado en tu models.py, estos son los campos correctos.
        fields = [
            'first_name',
            'last_name_paterno',
            'last_name_materno',
            'apodo',
            'birth_date',
            'fallecimiento_date',
            'lugar_nacimiento',
            'foto_principal',
            'estudios',
            'ocupación',
            'relationship',
            'padre',
            'madre',
            'conyuge',
            'padrino_de_bautismo',
            'madrina_de_bautismo',
            'correomail',
            'phone_number',
            'address',
            'whatsapp',
            'facebook',
            'linkedin',
            'instagram',
            ]
        # Alternativamente, si quieres incluir todos los campos del modelo
        # excepto los auto-generados (como 'id'), puedes usar:
        # fields = '__all__'

        # Si quieres excluir algunos campos específicamente:
        # exclude = ['some_field_to_exclude', 'another_field_to_exclude']