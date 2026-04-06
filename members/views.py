import json
from collections import defaultdict

from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.urls import reverse_lazy
from django.contrib import messages
from django.views.generic import CreateView, UpdateView, DeleteView
from django.core.paginator import Paginator
from django.db.models.functions import ExtractDay, ExtractMonth
from django.template.loader import render_to_string

from weasyprint import HTML
import openpyxl

from .models import Member
from .forms import MemberForm


# =========================================================
# 🔥 DESCENDENCIA DINÁMICA
# =========================================================
def get_descendants_by_level(member, max_levels=5):
    levels = {}

    current_level = Member.objects.filter(
        Q(padre=member) | Q(madre=member)
    ).distinct().order_by('birth_date')

    for level in range(1, max_levels + 1):
        levels[level] = current_level

        current_level = Member.objects.filter(
            Q(padre__in=current_level) | Q(madre__in=current_level)
        ).distinct().order_by('birth_date')

        if not current_level.exists():
            break

    return levels


# =========================================================
# 🌳 ÁRBOL
# =========================================================
def get_node_data(member, level=0):
    foto = None
    if member.foto_principal:
        try:
            foto = member.foto_principal.url
        except Exception:
            pass

    conyuge_nombre = None
    conyuge_foto = None
    conyuge_pk = None

    if member.conyuge:
        conyuge_pk = member.conyuge.pk
        conyuge_nombre = f"{member.conyuge.first_name or ''} {member.conyuge.last_name_paterno or ''}".strip()
        if member.conyuge.foto_principal:
            try:
                conyuge_foto = member.conyuge.foto_principal.url
            except Exception:
                pass

    hijos = Member.objects.filter(
        Q(padre=member) | Q(madre=member)
    ).distinct().order_by('birth_date')

    children = [get_node_data(h, level + 1) for h in hijos]

    node = {
        "name": member.first_name or f"Miembro {member.pk}",
        "last_name": member.last_name_paterno or "",
        "pk": member.pk,
        "level": level,
        "foto": foto,
        "conyuge_nombre": conyuge_nombre,
        "conyuge_foto": conyuge_foto,
        "conyuge_pk": conyuge_pk,
    }

    if children:
        node["children"] = children

    return node


def member_tree_data(request):
    ancestros = Member.objects.filter(
        Q(padre__isnull=True) & Q(madre__isnull=True)
    )
    return JsonResponse([get_node_data(a) for a in ancestros], safe=False)


# =========================================================
# 📋 FILTROS Y LISTA
# =========================================================
def get_filtered_members(request):
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


def member_list(request):
    paginator = Paginator(get_filtered_members(request), 10)
    page = request.GET.get('page')
    members = paginator.get_page(page)

    return render(request, 'members/member_list.html', {
        'members': members,
        'query_params': request.GET
    })


# =========================================================
# 👤 DETAIL
# =========================================================
def member_detail(request, pk):
    member = get_object_or_404(
        Member.objects.select_related('padre', 'madre', 'conyuge'),
        pk=pk
    )

    edit_mode = request.GET.get('edit') == '1'
    form = None

    if edit_mode:
        if request.method == 'POST':
            form = MemberForm(request.POST, request.FILES, instance=member)
            if form.is_valid():
                form.save()
                messages.success(request, "Perfil actualizado")
                return redirect('members:member_detail', pk=member.pk)
        else:
            form = MemberForm(instance=member)

    descendants = get_descendants_by_level(member, 5)

    context = {
        'member': member,
        'edit_mode': edit_mode,
        'form': form,
        'relations': [
            ('Padre', member.padre),
            ('Madre', member.madre),
            ('Cónyuge', member.conyuge),
        ],
        'hijos': descendants.get(1, Member.objects.none()),
        'nietos': descendants.get(2, Member.objects.none()),
        'bisnietos': descendants.get(3, Member.objects.none()),
        'tataranietos': descendants.get(4, Member.objects.none()),
        'choznos': descendants.get(5, Member.objects.none()),
        'family_data_json': json.dumps(get_node_data(member)),
    }

    return render(request, 'members/member_detail.html', context)


# =========================================================
# 📄 PDF
# =========================================================
def export_member_pdf(request, pk):
    member = get_object_or_404(Member, pk=pk)
    hermanos = Member.objects.filter(
        Q(padre=member.padre) | Q(madre=member.madre)
    ).exclude(pk=member.pk).distinct() if (member.padre or member.madre) else Member.objects.none()
    
    descendants = get_descendants_by_level(member, 5)


    context = {
        'member': member,
        'hermanos': hermanos,
        'hijos': descendants.get(1, Member.objects.none()),
        'nietos': descendants.get(2, Member.objects.none()),
        'bisnietos': descendants.get(3, Member.objects.none()),
        'tataranietos': descendants.get(4, Member.objects.none()),
        'choznos': descendants.get(5, Member.objects.none()),
        'tree_data_json': json.dumps(get_node_data(member)),
        'MY_DOMAIN': request.build_absolute_uri('/')[:-1]
    }

    html = render_to_string('members/member_pdf_template.html', context)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Ficha_{member.pk}.pdf"'

    HTML(string=html, base_url=request.build_absolute_uri()).write_pdf(response)
    return response


# =========================================================
# 📊 EXCEL
# =========================================================
def export_members_excel(request):
    wb = openpyxl.Workbook()
    ws = wb.active

    ws.append(['Nombre', 'Apellido', 'Fecha Nacimiento'])

    for m in Member.objects.all():
        ws.append([
            m.first_name,
            m.last_name_paterno,
            m.birth_date.strftime('%d/%m/%Y') if m.birth_date else ""
        ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="familia.xlsx"'

    wb.save(response)
    return response


# =========================================================
# 📅 FECHAS
# =========================================================
def member_dates_query_view(request):
    members = get_filtered_members(request)

    return render(request, 'members/member_dates_query.html', {
        'members': members,
        'query_params': request.GET
    })


# =========================================================
# 🌳 RAMAS
# =========================================================
def members_by_family_branch_view(request):
    branches = defaultdict(list)

    for m in Member.objects.all():
        key = f"{m.last_name_paterno or ''} - {m.last_name_materno or ''}".strip()
        branches[key].append(m)

    return render(request, 'members/member_branches.html', {
        'sorted_branches': sorted(branches.items())
    })


# =========================================================
# 🧾 AJAX
# =========================================================
def validate_dni_ajax(request):
    dni = request.GET.get('dni')
    return JsonResponse({
        'is_taken': Member.objects.filter(dni=dni).exists() if dni else False
    })


# =========================================================
# 🧩 CRUD
# =========================================================
class MemberCreateView(CreateView):
    model = Member
    form_class = MemberForm
    template_name = 'members/member_form.html'
    success_url = reverse_lazy('members:member_list')


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