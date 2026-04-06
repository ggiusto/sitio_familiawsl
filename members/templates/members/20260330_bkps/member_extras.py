# members/templatetags/member_extras.py
# Este archivo define filtros personalizados para usar en las plantillas de Django.

from django import template

register = template.Library()

@register.filter
def get_form_field(form, field_name):
    """
    Permite acceder a un campo específico de un objeto 'form' de Django
    usando su nombre como una cadena (string).
    """
    try:
        return form[field_name]
    except (KeyError, TypeError):
        return None

@register.filter
def get_member_field(member, field_name):
    """
    Permite acceder a un atributo (campo) de un objeto 'Member'
    usando su nombre como una cadena (string).
    """
    return getattr(member, field_name, None)

@register.filter
def get_attribute(obj, attr_name):
    """
    Obtiene un atributo de un objeto dinámicamente.
    Uso en template: {{ objeto|get_attribute:"nombre_del_atributo" }}
    """
    return getattr(obj, attr_name, None)

@register.filter
def month_name(month_number):
    """
    Convierte un número de mes (1-12) en su nombre en español.
    Uso en template: {{ valor|month_name }}
    """
    months = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
        5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
        9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }
    try:
        return months.get(int(month_number), "")
    except (ValueError, TypeError):
        return ""