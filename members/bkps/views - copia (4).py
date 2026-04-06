import json
import os
import pandas as pd
from datetime import date

from django.conf import settings
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.core.paginator import Paginator  # IMPORTADO PARA PAGINACIÓN
from django.db import models
from django.db.models import Q
from django.db.models.functions import ExtractDay
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.views.generic import DetailView, CreateView, UpdateView, DeleteView

# ReportLab para PDF Profesional
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors

from .models import Member
from .forms import MemberForm

# =========================================================
# 1. FUNCIONES AUXILIARES (LÓGICA DE FILTRADO Y NEGOCIO)
# =========================================================

def get_filtered_members(request):
    """Lógica de filtrado unificada con ordenamiento cronológico por día del mes"""
    members = Member.objects.all()
    q = request.GET.get('q')
    month_birth = request.GET.get('month_birth')
    month_death = request.GET.get('month_death')
    status = request.GET.get('status')

    # Filtro de búsqueda por texto
    if q:
        members = members.filter(
            Q(first_name__icontains=q) | 
            Q(last_name_paterno__icontains=q) | 
            Q(last_name_materno__icontains=q) |
            Q(apodo__icontains=q)
        )

    # Lógica de Filtrado por Mes y Ordenamiento por Día
    if month_birth and month_birth.isdigit():
        members = members.filter(birth_date__month=int(month_birth))
        members = members.annotate(birth_day=ExtractDay('birth_date')).order_by('birth_day')
    
    elif month_death and month_death.isdigit():
        members = members.filter(fallecimiento_date__month=int(month_death))
        members = members.annotate(death_day=ExtractDay('fallecimiento_date')).order_by('death_day')

    else:
        # Orden por defecto: Alfabético para que no se mezclen
        members = members.order_by('last_name_paterno', 'first_name')

    # Filtro de Estado Vital
    if status == 'vivos':
        members = members.filter(fallecimiento_date__isnull=True)
    elif status == 'fallecidos':
        members = members.filter(fallecimiento_date__isnull=False)
    
    return members

def calculate_age(birth_date):
    """Cálculo preciso de edad"""
    if not birth_date:
        return 0
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

# =========================================================
# 2. VISTAS PRINCIPALES (CON PAGINACIÓN)
# =========================================================

def member_list_view(request):
    """Vista de lista corregida para ver todos los miembros paginados"""
    member_list = get_filtered_members(request)
    
    # Mostramos 20 miembros por página para evitar el sesgo de apellidos A y B
    paginator = Paginator(member_list, 20) 
    page_number = request.GET.get('page')
    members = paginator.get_page(page_number)
    
    return render(request, 'members/member_list.html', {
        'members': members,
        'query_params': request.GET
    })

# =========================================================
# 3. VISTAS DE EXPORTACIÓN (REPORTLAB Y PANDAS COMPLETOS)
# =========================================================

def export_members_pdf(request):
    """Genera la Crónica Familiar Completa"""
    members = get_filtered_members(request)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="cronica_familiar.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    
    # --- CARÁTULA ---
    p.setFont("Helvetica-Bold", 28)
    p.setFillColor(colors.indigo)
    p.drawCentredString(width/2, height - 10*cm, "FAMILIA BIDART SOLARI y PARIENTES")
    
    p.setFont("Helvetica", 14)
    p.setFillColor(colors.black)
    p.drawCentredString(width/2, height - 11.5*cm, f"Reporte generado el {date.today().strftime('%d/%m/%Y')}")

    # --- ÍNDICE ALFABÉTICO ---
    indices = {}
    for m in members:
        letra = (m.last_name_paterno or "S")[0].upper()
        indices[letra] = indices.get(letra, 0) + 1

    p.setFont("Helvetica-Bold", 16)
    p.drawString(2*cm, height - 14*cm, "Índice de Apellidos:")
    
    ix_y = height - 15.5*cm
    p.setFont("Helvetica", 11)
    col = 0
    for letra, cantidad in sorted(indices.items()):
        p.drawString(2*cm + (col * 4.5*cm), ix_y, f"Letra {letra}: ({cantidad})")
        ix_y -= 0.8*cm
        if ix_y < 4*cm:
            ix_y = height - 15.5*cm
            col += 1
    p.showPage()

    # --- LISTADO DETALLADO ---
    y_position = height - 2*cm
    row_height = 4.0 * cm 
    photo_size = 2.8 * cm
    margin_left = 1.5 * cm

    for m in members:
        if y_position < 4*cm:
            p.showPage()
            y_position = height - 2*cm

        # Foto
        draw_photo = False
        if m.foto_principal:
            try:
                img_path = os.path.join(settings.MEDIA_ROOT, m.foto_principal.name)
                if os.path.exists(img_path):
                    p.drawImage(ImageReader(img_path), margin_left, y_position - photo_size, 
                                width=photo_size, height=photo_size, preserveAspectRatio=True, mask='auto')
                    draw_photo = True
            except: pass
        if not draw_photo:
            p.setStrokeColor(colors.lightgrey)
            p.circle(margin_left + photo_size/2, y_position - photo_size/2, photo_size/2, stroke=1, fill=0)

        # Texto
        text_x = margin_left + photo_size + 0.6*cm
        curr_y = y_position - 0.6*cm
        p.setFont("Helvetica-Bold", 13)
        p.drawString(text_x, curr_y, f"{m.first_name} {m.last_name_paterno} {m.last_name_materno or ''}")
        
        if m.apodo:
            curr_y -= 0.6*cm
            p.setFont("Helvetica-Oblique", 11)
            p.setFillColor(colors.gray)
            p.drawString(text_x, curr_y, f'"{m.apodo}"')
            p.setFillColor(colors.black)

        curr_y -= 0.7*cm
        p.setFont("Helvetica", 10)
        nac_str = m.birth_date.strftime('%d/%m/%Y') if m.birth_date else "No registrada"
        p.drawString(text_x, curr_y, f"Nacimiento: {nac_str}")
        
        curr_y -= 0.5*cm
        if m.fallecimiento_date:
            p.setFillColor(colors.darkred)
            p.drawString(text_x, curr_y, f"Fallecimiento: {m.fallecimiento_date.strftime('%d/%m/%Y')}")
            p.setFillColor(colors.black)
        else:
            age = calculate_age(m.birth_date)
            p.drawString(text_x, curr_y, f"Estado: Presente ({age} años)")

        # QR
        if m.qr_code:
            try:
                qr_path = os.path.join(settings.MEDIA_ROOT, m.qr_code.name)
                p.drawImage(ImageReader(qr_path), width - 4.5*cm, y_position - photo_size, width=photo_size, height=photo_size)
            except: pass

        y_position -= row_height
        p.setDash(1, 3)
        p.setStrokeColor(colors.silver)
        p.line(margin_left, y_position + 0.5*cm, width - margin_left, y_position + 0.5*cm)
        p.setDash()

    p.save()
    return response

def export_members_excel(request):
    """Exportación completa a Excel"""
    members = get_filtered_members(request)
    data = []
    for m in members:
        data.append({
            'Nombre': m.first_name,
            'Apellido Paterno': m.last_name_paterno,
            'Apellido Materno': m.last_name_materno or '',
            'Apodo': m.apodo or '',
            'DNI': getattr(m, 'dni', '---'),
            'Fecha Nacimiento': m.birth_date,
            'Estado': 'Fallecido' if m.fallecimiento_date else 'Vivo',
            'Email': getattr(m, 'correomail', ''),
        })
    df = pd.DataFrame(data)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=registro_familiar_completo.xlsx'
    with pd.ExcelWriter(response, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Integrantes')
        worksheet = writer.sheets['Integrantes']
        for i, col in enumerate(df.columns):
            column_len = max(df[col].astype(str).str.len().max(), len(col)) + 2
            worksheet.set_column(i, i, column_len)
    return response

# =========================================================
# 4. VISTAS CRUD (CREATE, UPDATE, DELETE, DETAIL)
# =========================================================

class MemberCreateView(CreateView):
    model = Member
    form_class = MemberForm
    template_name = 'members/member_form.html'
    success_url = reverse_lazy('members:member_list')
    def form_valid(self, form):
        messages.success(self.request, "Miembro creado exitosamente.")
        return super().form_valid(form)

class MemberUpdateView(UpdateView):
    model = Member
    form_class = MemberForm
    template_name = 'members/member_form.html'
    success_url = reverse_lazy('members:member_list')
    def form_valid(self, form):
        messages.info(self.request, "Información actualizada.")
        return super().form_valid(form)

class MemberDeleteView(DeleteView):
    model = Member
    template_name = 'members/member_confirm_delete.html'
    success_url = reverse_lazy('members:member_list')

class MemberDetailView(DetailView):
    model = Member
    template_name = 'members/member_detail.html'
    context_object_name = 'member'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        m = self.get_object()
        context['edit_mode'] = self.request.GET.get('edit') == '1' or True 
        def fetch_descendants(qs):
            ids = qs.values_list('id', flat=True)
            return Member.objects.filter(Q(padre_id__in=ids) | Q(madre_id__in=ids)).distinct()
        hijos = Member.objects.filter(Q(padre=m) | Q(madre=m)).distinct()
        context['hijos_list'] = hijos
        context['nietos_list'] = fetch_descendants(hijos)
        context['bisnietos_list'] = fetch_descendants(context['nietos_list'])
        context['padre'] = m.padre
        context['madre'] = m.madre
        context['conyuge'] = getattr(m, 'conyuge', None)
        return context

# =========================================================
# 5. ÁRBOL, RAMAS Y AJAX
# =========================================================

def family_tree_view(request):
    """Vista del árbol interactivo"""
    return render(request, 'members/family_tree.html')

def family_tree_data_view(request, pk):
    """JSON para D3.js"""
    member = get_object_or_404(Member, pk=pk)
    def get_data(m, visited=None):
        if visited is None: visited = set()
        if m.pk in visited: return None
        visited.add(m.pk)
        return {
            "name": f"{m.first_name} {m.last_name_paterno}",
            "id": m.pk,
            "img": m.foto_principal.url if m.foto_principal else None,
            "children": [get_data(h, visited) for h in Member.objects.filter(Q(padre=m) | Q(madre=m)).distinct() if h.pk not in visited]
        }
    return JsonResponse(get_data(member))

def members_by_family_branch_view(request):
    """Agrupación por ramas de apellidos corregida"""
    members = Member.objects.all().order_by('last_name_paterno')
    branches = {}
    for m in members:
        key = f"{m.last_name_paterno} {m.last_name_materno or ''}".strip().upper()
        if key not in branches: branches[key] = []
        branches[key].append(m)
    return render(request, 'members/members_by_family_branch.html', {
        'sorted_branches': sorted(branches.items())
    })

def validate_dni_ajax(request):
    dni = request.GET.get('dni', None)
    is_taken = Member.objects.filter(dni__iexact=dni).exists()
    return JsonResponse({'is_taken': is_taken})

def member_dates_query_view(request):
    """Consulta de efemérides (Sin paginación para ver todo el mes)"""
    members = get_filtered_members(request)
    return render(request, 'members/member_dates_query.html', {
        'members': members,
        'query_params': request.GET
    })

from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML, CSS
from .models import Member
import tempfile

def export_member_pdf(request, pk):
    # Usar get_object_or_404 es mejor práctica
    member = get_object_or_404(Member, pk=pk)
    
    context = {
        'member': member,
        'siblings': member.get_siblings() if hasattr(member, 'get_siblings') else [],
        'MY_DOMAIN': request.build_absolute_uri('/')[:-1] # Dinámico
    }

    html_string = render_to_string('members/member_pdf_template.html', context)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Ficha_{member.last_name_paterno}.pdf"'
    
    # IMPORTANTE: Solo una ejecución de HTML().write_pdf
    # El base_url es lo que evita el error de "Relative URI"
    HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf(response)
    
    return response