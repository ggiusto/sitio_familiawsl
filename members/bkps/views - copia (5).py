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
    Incluye nivel de generación para colores y URL de foto para los nodos.
    Muestra el nombre completo del titular y abrevia el del cónyuge si existiera.
    """
    
    # Función interna para abreviar nombres: "PrimerNombre I."
    def abreviar_nombre(nombre_completo):
        if not nombre_completo:
            return ""
        partes = nombre_completo.split()
        if len(partes) > 1:
            return f"{partes[0]} {partes[1][0]}."
        return partes[0]

    # Nombre del titular completo
    nombre_titular = member.first_name if member.first_name else f"Miembro {member.pk}"
    
    conyuge_info = ""
    # Si tienes el campo conyuge implementado en el modelo, podrías activarlo así:
    # if member.conyuge:
    #     conyuge_info = f" & {abreviar_nombre(member.conyuge.first_name)}"

    # Obtener URL de la foto (usando el nombre correcto del campo: foto_principal)
    foto_url = member.foto_principal.url if member.foto_principal else None
    if member.foto_principal:
        try:
            foto_url = member.foto_principal.url
        except (ValueError, AttributeError):
            foto_url = None

    # RECURSIÓN PARA DESCENDIENTES:
    # Buscamos todos los miembros que tengan a este miembro como padre O como madre
    children_list = []
    hijos = Member.objects.filter(Q(padre=member) | Q(madre=member)).distinct().order_by('birth_date')
    descendientes = Member.objects.filter(
        Q(padre=member) | Q(madre=member)
    ).distinct().order_by('birth_date')

    for child in hijos:
        children_list.append(get_node_data(child, level + 1))

    return {
        "name": member.first_name,
        "last_name": member.last_name_paterno,
        "pk": member.pk,
        "level": level,  
        "foto": foto_url, 
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
    member = get_object_or_404(Member, pk=pk)
    edit_mode = request.GET.get('edit') == 'True'
    form = None

    # Manejo de edición rápida desde la misma vista
    if edit_mode:
        if request.method == 'POST':
            # Procesa los cambios enviados
            form = MemberForm(request.POST, request.FILES, instance=member)
            if form.is_valid():
                form.save()
                messages.success(request, f"¡Perfil de {member.first_name} actualizado!")
                return redirect('members:member_detail', pk=member.pk)
        else:
            # Carga el formulario con los datos actuales
            form = MemberForm(instance=member)

    # Lógica de Relaciones para las tablas de la Biografía
    # Hijos
    hijos = Member.objects.filter(Q(padre=member) | Q(madre=member)).distinct().order_by('birth_date')
    # Cálculo de descendencia extendida
    # Nietos: Hijos de los hijos
    nietos = Member.objects.filter(Q(padre__in=hijos) | Q(madre__in=hijos)).distinct()
    # Bisnietos: Hijos de los nietos
    bisnietos = Member.objects.filter(Q(padre__in=nietos) | Q(madre__in=nietos)).distinct()
    # Tataranietos: Hijos de los bisnietos
    tataranietos = Member.objects.filter(Q(padre__in=bisnietos) | Q(madre__in=bisnietos)).distinct()
    # Generación de datos JSON para el árbol interactivo D3.js
    family_hierarchy = get_node_data(member)
    family_data_json = json.dumps(family_hierarchy)

    # Filtrar campos automáticos para no mostrarlos en la tabla biográfica
    omit_fields = [
        'id', 'first_name', 'last_name_paterno', 'last_name_materno', 
        'last_name_casada', 'foto', 'qr_code', 'biografia', 'parent'
    ]
    general_info_fields = [
        f for f in member._meta.fields if f.name not in omit_fields
    ]
    # Creamos una lista de relaciones para el bucle del template
    relations = [
        ('Padre', member.padre),
        ('Madre', member.madre),
        ('Cónyuge', member.conyuge),
    ]
    context = {
        'member': member,
        'edit_mode': edit_mode,
        'relations': relations,
        'form': form,
        'padre': member.padre, # Antes era member.parent
        'madre': member.madre, # Nuevo campo según tu modelo
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
    template_name = 'members/member_form.html'
    
    def get_success_url(self):
        return reverse_lazy('members:member_detail', kwargs={'pk': self.object.pk})

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
    """Vista agrupada por ramas familiares"""
    members = Member.objects.all().order_by('last_name_paterno')
    return render(request, 'members/member_list.html', {
        'members': members,
        'is_branch_view': True
    })