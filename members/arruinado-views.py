import json
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.safestring import mark_safe
import os
import pandas as pd
from datetime import date

from django.conf import settings
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from django.db.models.functions import ExtractDay, ExtractMonth
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.views.generic import CreateView, UpdateView, DeleteView 
from django.template.loader import render_to_string

from weasyprint import HTML, CSS
import tempfile
import openpyxl

from .models import Member
from .forms import MemberForm


# =========================================================
# 1. FUNCIONES AUXILIARES Y LÓGICA DE ÁRBOL
# =========================================================

def get_node_data(member, level=0):
    """
    Construye la jerarquía para D3.js buscando hijos por campos padre/madre.
    Optimizado para evitar errores de URL y múltiples consultas a DB.
    """
    # Límite de seguridad para evitar recursión infinita en caso de datos circulares
    if not member or level > 10:
        return None

    # 1. Preparar la estructura básica con manejo seguro de la foto
    foto_url = ""
    if member.foto:
        try:
            foto_url = member.foto.url
        except ValueError:
            foto_url = ""

    node = {
        'name': member.first_name,
        'last_name': member.last_name_paterno or "",
        'pk': member.pk,
        'foto': foto_url,
        'children': []
    }

    # 2. Búsqueda de hijos
    # Usamos select_related('padre', 'madre') para que la recursión sea más rápida
    hijos_queryset = Member.objects.filter(
        Q(padre=member) | Q(madre=member)
    ).select_related('padre', 'madre').distinct().order_by('birth_date')

    # 3. Recursión
    for hijo in hijos_queryset:
        child_node = get_node_data(hijo, level + 1)
        if child_node:
            node['children'].append(child_node)

    # D3.js a veces prefiere que si no hay hijos, la clave 'children' no exista 
    # o esté vacía. Mantenerla como [] es correcto para la mayoría de implementaciones.
    return node
def member_tree_data(request,member_id):
    member = get_object_or_404(Member, pk=member_id)
    data = get_node_data(member)
    return JsonResponse(data, safe=False)
    ancestros = Member.objects.filter(padre__isnull=True, madre__isnull=True)

    # 2. Si no hay ancestros absolutos, tomamos a los miembros de la primera generación definida
    if not ancestros.exists():
        ancestros = Member.objects.filter(relationship='TATARABUELO')

    # 3. Construimos la data recursiva
    # Usamos 'm' para iterar y filtramos resultados None
    family_list = []
    for m in ancestros:
        node = get_node_data(m)
        if node:
            family_list.append(node)

    # 4. CORRECCIÓN CRÍTICA PARA D3.JS:
    # D3 requiere UN solo objeto raíz. Si hay varios ancestros, 
    # los envolvemos en un nodo virtual "Familia" para que todos se vean.
    if len(family_list) > 1:
        data_to_send = {
            "name": "Raíces Familiares",
            "first_name": "Linaje",
            "visual_paterno": "",
            "children": family_list
        }
    elif len(family_list) == 1:
        data_to_send = family_list[0]
    else:
        data_to_send = {}

    return JsonResponse(data_to_send, safe=False)

def get_family_structure(member):
    """
    Organiza los datos básicos para exportación PDF.
    Se corrige el error de acceso a .children utilizando el filtro de Member.
    """
    # Obtenemos los hijos buscando donde el miembro actual sea padre o madre
    hijos = Member.objects.filter(
        Q(padre=member) | Q(madre=member)
    ).distinct().order_by('birth_date')

    return {
        'member': member,
        'padre': member.padre,
        'madre': member.madre,
        'hijos': hijos
    }

def get_filtered_members(request):
    """Lógica de filtrado para la lista principal y consultas de fechas"""
    members = Member.objects.all()
    q = request.GET.get('q')
    month_birth = request.GET.get('month_birth')
    month_death = request.GET.get('month_death')
    
    if q:
        members = members.filter(
            Q(first_name__icontains=q) | 
            Q(last_name_paterno__icontains=q) | 
            Q(apodo__icontains=q)
        )
    
    if month_birth:
        members = members.filter(birth_date__month=month_birth)
        
    if month_death:
        members = members.filter(death_date__month=month_death)

    return members.annotate(
        birth_day=ExtractDay('birth_date'),
        birth_month=ExtractMonth('birth_date')
    ).order_by('birth_month', 'birth_day', 'last_name_paterno')

# =========================================================
# 2. VISTAS PRINCIPALES (LISTA Y DETALLE)
# =========================================================

def member_list(request):
    members_list = get_filtered_members(request)
    paginator = Paginator(members_list, 10)
    page = request.GET.get('page')
    members = paginator.get_page(page)
    
    return render(request, 'members/member_list.html', {
        'members': members,
        'query_params': request.GET
    })

import json
import openpyxl
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.http import HttpResponse
from django.contrib import messages
from django.db.models import Q
from django.utils.safestring import mark_safe
from django.views.generic import CreateView, UpdateView, DeleteView

from .models import Member
from .forms import MemberForm

# Nota: Se asume que get_node_data está definida en este archivo o importada correctamente.

def member_detail(request, pk):
    # 1. OBTENCIÓN DEL OBJETO (Optimizado)
    member = get_object_or_404(
        Member.objects.select_related('padre', 'madre', 'conyuge'), 
        pk=pk
    )
    
    edit_mode = request.GET.get('edit') == 'True'
    form = None

    # 2. MANEJO DE EDICIÓN (Mantenemos tu lógica)
    if edit_mode:
        if request.method == 'POST':
            form = MemberForm(request.POST, request.FILES, instance=member)
            if form.is_valid():
                form.save()
                messages.success(request, f"¡Perfil de {member.first_name} actualizado!")
                return redirect('members:member_detail', pk=member.pk)
        else:
            form = MemberForm(instance=member)

    # 3. LÓGICA DE DESCENDENCIA (Mantenemos tus consultas para las tablas)
    hijos = Member.objects.filter(Q(padre=member) | Q(madre=member)).distinct().order_by('birth_date')
    nietos = Member.objects.filter(Q(padre__in=hijos) | Q(madre__in=hijos)).distinct().order_by('birth_date')
    bisnietos = Member.objects.filter(Q(padre__in=nietos) | Q(madre__in=nietos)).distinct().order_by('birth_date')
    tataranietos = Member.objects.filter(Q(padre__in=bisnietos) | Q(madre__in=bisnietos)).distinct().order_by('birth_date')
    choznos = Member.objects.filter(Q(padre__in=tataranietos) | Q(madre__in=tataranietos)).distinct().order_by('birth_date')

    # 4. GENERACIÓN DEL JSON PARA D3.JS (Forzar JSON Seguro)
    try:
        # Llamamos a la función recursiva para obtener la estructura del árbol
        family_hierarchy = get_node_data(member)
        # IMPORTANTE: mark_safe + json.dumps evita el error de "Unexpected token &" en el navegador
        family_data_json = mark_safe(json.dumps(family_hierarchy))
    except Exception as e:
        # Fallback seguro en caso de error en la recursión o datos
        fallback_data = {"name": member.first_name, "error": str(e)}
        family_data_json = mark_safe(json.dumps(fallback_data))

    # 5. FILTRADO DE CAMPOS (Mantenemos tu lógica de tabla biográfica)
    omit_fields = [
        'id', 'first_name', 'last_name_paterno', 'last_name_materno', 
        'last_name_casada', 'foto', 'qr_code', 'biografia', 'parent', 
        'foto_principal', 'slug', 'created_at', 'updated_at'
    ]
    general_info_fields = [f for f in member._meta.fields if f.name not in omit_fields and not f.is_relation]

    # 6. CONTEXTO FINAL
    context = {
        'member': member,
        'edit_mode': edit_mode,
        'form': form,
        'hijos': hijos,
        'nietos': nietos,
        'bisnietos': bisnietos,
        'tataranietos': tataranietos,
        'choznos': choznos,
        'family_data_json': family_data_json,  # El JSON ahora es seguro para JavaScript
        'general_info_fields': general_info_fields,
        'relations': [
            ('Padre', member.padre), 
            ('Madre', member.madre), 
            ('Cónyuge', member.conyuge)
        ],
    }
    
    return render(request, 'members/member_detail.html', context)

# =========================================================
# 3. VISTAS DE FORMULARIO (CRUD)
# =========================================================

class MemberCreateView(CreateView):
    model = Member
    form_class = MemberForm
    template_name = 'members/member_form.html'
    success_url = reverse_lazy('members:member_list')

    def form_valid(self, form):
        messages.success(self.request, "Miembro creado con éxito.")
        return super().form_valid(form)

class MemberUpdateView(UpdateView):
    model = Member
    form_class = MemberForm
    template_name = 'members/member_form.html'

    def get_success_url(self):
        # Al terminar, redirige al detalle del miembro editado
        return reverse_lazy('members:member_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, "Perfil actualizado correctamente.")
        return super().form_valid(form)

class MemberDeleteView(DeleteView):
    model = Member
    template_name = 'members/member_confirm_delete.html'
    success_url = reverse_lazy('members:member_list')

# =========================================================
# 4. EXPORTACIÓN (EXCEL Y PDF)
# =========================================================

def export_members_excel(request):
    """Genera archivo Excel de la lista completa"""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Familiares"

    columns = ['Nombre', 'Apellido Paterno', 'Apellido Materno', 'Apodo', 'Fecha Nacimiento', 'DNI']
    ws.append(columns)

    for member in Member.objects.all().order_by('last_name_paterno', 'first_name'):
        ws.append([
            member.first_name,
            member.last_name_paterno,
            member.last_name_materno or "",
            member.apodo or "",
            member.birth_date.strftime('%d/%m/%Y') if member.birth_date else "",
            member.dni or ""
        ])

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="Lista_Familiares.xlsx"'
    wb.save(response)
    return response

def export_member_pdf(request, pk):
    """
    Genera y exporta un archivo PDF detallado de un miembro de la familia,
    incluyendo su árbol genealógico, hermanos y descendencia extendida.
    """
    from django.db.models import Q
    from django.template.loader import render_to_string
    from django.http import HttpResponse
    from django.shortcuts import get_object_or_404
    from weasyprint import HTML
    import json

    # 0. Obtención del miembro principal
    member = get_object_or_404(Member, pk=pk)
    
    # 1. Obtención de Hermanos (Mismo padre O misma madre, excluyendo al titular)
    # Se utiliza .distinct() para evitar duplicados si comparten ambos padres
    hermanos = []
    if member.padre or member.madre:
        hermanos = Member.objects.filter(
            Q(padre=member.padre if member.padre else None) | 
            Q(madre=member.madre if member.madre else None)
        ).exclude(pk=member.pk).distinct().order_by('birth_date')

    # 2. Obtención encadenada de generaciones (Descendencia)
    # Hijos
    hijos = Member.objects.filter(
        Q(padre=member) | Q(madre=member)
    ).distinct().order_by('birth_date')
    
    # Nietos (Hijos de los hijos)
    nietos = Member.objects.filter(
        Q(padre__in=hijos) | Q(madre__in=hijos)
    ).distinct().order_by('birth_date')
    
    # Bisnietos (Hijos de los nietos)
    bisnietos = Member.objects.filter(
        Q(padre__in=nietos) | Q(madre__in=nietos)
    ).distinct().order_by('birth_date')
    
    # Tataranietos (Hijos de los bisnietos)
    tataranietos = Member.objects.filter(
        Q(padre__in=bisnietos) | Q(madre__in=bisnietos)
    ).distinct().order_by('birth_date')

    # 3. Datos para el esquema genealógico (Estructura JSON para el SVG)
    # get_node_data debe ser tu función recursiva que ya tienes definida en views.py
    tree_data = get_node_data(member)

    # 4. Construcción del contexto para el template
    context = {
        'member': member,
        'padre': member.padre,
        'madre': member.madre,
        'hermanos': hermanos,
        'hijos': hijos,
        'nietos': nietos,
        'bisnietos': bisnietos,
        'tataranietos': tataranietos,
        'tree_data': tree_data,  # Se pasa para renderizar el esquema visual
        'tree_data_json': json.dumps(tree_data),
        'MY_DOMAIN': request.build_absolute_uri('/')[:-1]
    }

    # 5. Generación del PDF mediante WeasyPrint
    html_string = render_to_string('members/member_pdf_template.html', context)
    
    response = HttpResponse(content_type='application/pdf')
    
    # Limpiamos el nombre del archivo: Apellido_Nombre_ID.pdf
    safe_last_name = (member.last_name_paterno or "Miembro").replace(" ", "_")
    filename = f"Ficha_{safe_last_name}_{member.pk}.pdf"
    
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # Generar el PDF. base_url permite que WeasyPrint resuelva rutas de imágenes y CSS
    HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf(response)
    
    return response

# =========================================================
# 5. CONSULTAS ESPECIALES Y AJAX
# =========================================================

def member_dates_query_view(request):
    """Vista para consultar fechas de nacimiento/defunción por mes"""
    members = get_filtered_members(request)
    return render(request, 'members/member_dates_query.html', {
        'members': members,
        'query_params': request.GET
    })

def validate_dni_ajax(request):
    """Validación de DNI en tiempo real para el formulario"""
    dni = request.GET.get('dni', None)
    if dni:
        is_taken = Member.objects.filter(dni__iexact=dni).exists()
        return JsonResponse({'is_taken': is_taken})
    return JsonResponse({'error': 'No DNI provided'}, status=400)

def members_by_family_branch_view(request):
    """Vista agrupada por combinación de Apellido Paterno + Apellido Materno"""
    from collections import defaultdict
    
    # 1. Obtenemos todos los miembros ordenados por ambos apellidos
    all_members = Member.objects.all().order_by('last_name_paterno', 'last_name_materno', 'first_name')
    
    # 2. Agrupamos en un diccionario usando la combinación como clave
    branches_dict = defaultdict(list)
    
    for member in all_members:
        # Extraemos y limpiamos los apellidos
        paterno = member.last_name_paterno.strip() if member.last_name_paterno else ""
        materno = member.last_name_materno.strip() if member.last_name_materno else ""
        
        # Construimos la clave de la rama (Ej: "Bidart - Almada")
        if paterno and materno:
            branch_key = f"{paterno} - {materno}"
        elif paterno:
            branch_key = paterno
        elif materno:
            branch_key = materno
        else:
            branch_key = "Sin Apellidos Definidos"
            
        branches_dict[branch_key].append(member)
    
    # 3. Convertimos a una lista de tuplas y ordenamos alfabéticamente por la clave de la rama
    sorted_branches = sorted(branches_dict.items())
    
    return render(request, 'members/member_branches.html', {
        'sorted_branches': sorted_branches,
    })