# members/admin.py
from django.contrib import admin
from .models import Member

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    # Para mostrar el valor legible de la relación, definimos un método
    def relationship_display(self, obj):
        return obj.get_relationship_display()
    relationship_display.short_description = "Relación"

    list_display = (
        'first_name',
        'last_name_paterno',
        'relationship_display',  # sustituimos 'relationship' por nuestro método
        'padre',
        'madre',
        'conyuge',
    )
    search_fields = (
        'first_name',
        'last_name_paterno',
        'last_name_materno',
    )
    list_filter = (
        'relationship',  # ahora sí corresponde a un Field real
    )

    # Para optimizar consultas al mostrar la lista
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('padre', 'madre', 'conyuge')
