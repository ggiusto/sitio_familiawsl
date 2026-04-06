import json
import os
import pandas as pd
from datetime import date

from django.conf import settings
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Q
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
    Función recursiva para jerarquía D3.js.
    Incluye nivel de generación, fotos y datos del cónyuge (nombre, foto y PK).
    """
    
    # 1. PROCESAMIENTO DE IMAGEN DEL TITULAR
    foto_url = None
    if member.foto_principal:
        try:
            foto_url = member.foto_principal.url
        except (ValueError, AttributeError):
            foto_url = None

    # 2. LÓGICA PARA EL CÓNYUGE (Modificación incorporada)
    # Obtenemos nombre, foto y PK del cónyuge si existe el registro
    conyuge_nombre = None
    conyuge_foto = None
    conyuge_pk = None # Importante para clipPaths únicos

    if member.conyuge:
        conyuge_pk = member.conyuge.pk
        conyuge_nombre = f"{member.conyuge.first_name} {member.conyuge.last_name_paterno}"
        
        # Foto del cónyuge
        if member.conyuge.foto_principal:
            try:
                conyuge_foto = member.conyuge.foto_principal.url
            except (ValueError, AttributeError):
                conyuge_foto = None

    # 3. RECURSIÓN PARA DESCENDIENTES
    children_list = []
    # Buscamos hijos donde el miembro actual sea padre o madre
    hijos = Member.objects.filter(
        Q(padre=member) | Q(madre=member)
    ).distinct().order_by('birth_date')

    for child in hijos:
        children_list.append(get_node_data(child, level + 1))

    # 4. ESTRUCTURA DE RETORNO (JSON)
    return {
        "name": member.first_name if member.first_name else f"Miembro {member.pk}",
        "last_name": member.last_name_paterno,
        "pk": member.pk,
        "level": level,  
        "foto": foto_url, 
        "conyuge_nombre": conyuge_nombre,
        "conyuge_foto": conyuge_foto,
        "conyuge_pk": conyuge_pk, # Útil para los ID de clipPath en el frontend
        "children": children_list
    }
def member_tree_data(request):
    """
    Esta función sirve para inicializar el árbol general 
    buscando a los ancestros (los que no tienen padre definido)
    """
    ancestros = Member.objects.filter(parent__isnull=True)
    data = [get_node_data(a) for a in ancestros]
    return JsonResponse(data, safe=False)

def get_family_structure(member):
    """Organiza los datos básicos para exportación PDF"""
    hijos = member.children.all().order_by('birth_date')
    return {
        'member': member,
        'padre_madre': member.padre,
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

def member_detail(request, pk):
    # Obtenemos el miembro con select_related para minimizar consultas a padres/cónyuge
    member = get_object_or_404(
        Member.objects.select_related('padre', 'madre', 'conyuge'), 
        pk=pk
    )
    
    edit_mode = request.GET.get('edit') == 'True'
    form = None

    # 1. MANEJO DE EDICIÓN
    if edit_mode:
        if request.method == 'POST':
            form = MemberForm(request.POST, request.FILES, instance=member)
            if form.is_valid():
                form.save()
                messages.success(request, f"¡Perfil de {member.first_name} actualizado!")
                return redirect('members:member_detail', pk=member.pk)
        else:
            form = MemberForm(instance=member)

    # 2. LÓGICA DE RELACIONES PARA TABLAS BIOGRÁFICAS
    # Usamos prefetch_related o select_related para optimizar el rendimiento del árbol
    hijos = Member.objects.filter(
        Q(padre=member) | Q(madre=member)
    ).distinct().order_by('birth_date')

    nietos = Member.objects.filter(
        Q(padre__in=hijos) | Q(madre__in=hijos)
    ).distinct().order_by('birth_date')

    bisnietos = Member.objects.filter(
        Q(padre__in=nietos) | Q(madre__in=nietos)
    ).distinct().order_by('birth_date')

    tataranietos = Member.objects.filter(
        Q(padre__in=bisnietos) | Q(madre__in=bisnietos)
    ).distinct().order_by('birth_date')

    # 3. GENERACIÓN DE DATOS PARA EL ÁRBOL D3.JS
    # get_node_data debe estar definida en el mismo archivo o importada
    try:
        family_hierarchy = get_node_data(member)
        family_data_json = json.dumps(family_hierarchy)
    except Exception as e:
        # Fallback en caso de error de serialización para no romper la página
        family_data_json = json.dumps({"name": member.first_name, "error": str(e)})

    # 4. FILTRADO DE CAMPOS PARA LA TABLA DE INFORMACIÓN GENERAL
    # Lista de campos técnicos o redundantes que no queremos en la tabla visual
    omit_fields = [
        'id', 'first_name', 'last_name_paterno', 'last_name_materno', 
        'last_name_casada', 'foto', 'qr_code', 'biografia', 'parent', 
        'foto_principal', 'slug', 'created_at', 'updated_at'
    ]
    
    general_info_fields = [
        f for f in member._meta.fields 
        if f.name not in omit_fields and not f.is_relation
    ]

    # 5. LISTA DE RELACIONES DIRECTAS (Para la cabecera o info rápida)
    relations = [
        ('Padre', member.padre),
        ('Madre', member.madre),
        ('Cónyuge', member.conyuge),
    ]

    # 6. CONTEXTO Y RENDERIZADO
    context = {
        'member': member,
        'edit_mode': edit_mode,
        'relations': relations,
        'form': form,
        'padre': member.padre,
        'madre': member.madre,
        'hijos': hijos,
        'nietos': nietos,
        'bisnietos': bisnietos,
        'tataranietos': tataranietos,
        'family_data_json': family_data_json,
        'general_info_fields': general_info_fields,
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
    template_name = 'members/member_form.html' # Asegúrate de que esta sea la ruta a tu template

    def get_success_url(self):
        # Al terminar, redirige al detalle del miembro editado
        return reverse_lazy('members:member_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        # Opcional: puedes agregar un mensaje de éxito
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
    """Genera ficha individual en PDF usando WeasyPrint"""
    member = get_object_or_404(Member, pk=pk)
    family_data = get_family_structure(member)
    
    context = {
        **family_data,
        'MY_DOMAIN': request.build_absolute_uri('/')[:-1]
    }

    html_string = render_to_string('members/member_pdf_template.html', context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Ficha_{member.last_name_paterno}.pdf"'
    
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