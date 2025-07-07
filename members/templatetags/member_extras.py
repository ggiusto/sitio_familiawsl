# members/templatetags/member_extras.py
# Este archivo define filtros personalizados para usar en las plantillas de Django.

from django import template # Importa el módulo template de Django.

register = template.Library() # Crea una instancia de Library para registrar los filtros.

@register.filter # Decorador que registra la función como un filtro de plantilla.
def get_form_field(form, field_name):
    """
    Permite acceder a un campo específico de un objeto 'form' de Django
    usando su nombre como una cadena (string).

    Esto es útil cuando tienes una lista de nombres de campos (ej. info_fields)
    y quieres iterar sobre ellos para obtener y mostrar el objeto de campo
    real del formulario.

    Parámetros:
    - form: El objeto formulario de Django (ej. 'form' en member_form.html).
    - field_name: Una cadena que representa el nombre del campo (ej. "first_name").

    Retorna:
    - El objeto de campo del formulario si existe, o None si el nombre del campo no es válido.
    """
    try:
        return form[field_name] # Intenta acceder al campo del formulario por su nombre.
    except KeyError:
        # Si el nombre del campo no existe en el formulario, retorna None
        # para evitar un error y permitir que la plantilla continúe renderizándose.
        return None

@register.filter # Decorador que registra la función como un filtro de plantilla.
def get_member_field(member, field_name):
    """
    Permite acceder a un atributo (campo) de un objeto 'Member' (o cualquier modelo)
    usando su nombre como una cadena (string).

    Esto es útil en la plantilla 'member_detail.html' para mostrar dinámicamente
    la información de un miembro basándose en una lista de nombres de campos.

    Parámetros:
    - member: El objeto del modelo Member (o cualquier otro objeto).
    - field_name: Una cadena que representa el nombre del atributo (campo).

    Retorna:
    - El valor del atributo si existe, o None si el atributo no existe.
    """
    return getattr(member, field_name, None) # Usa getattr para obtener el atributo de forma segura.

