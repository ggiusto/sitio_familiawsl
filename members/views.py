import json
from django.views.generic import DetailView, ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.shortcuts import render, get_object_or_404, redirect
from .models import Member
from .forms import MemberForm
from django.db import models # Import models to use Q objects

class MemberListView(ListView):
    model = Member
    template_name = 'members/member_list.html'
    context_object_name = 'members'
    paginate_by = 20


class MemberCreateView(CreateView):
    model = Member
    form_class = MemberForm
    template_name = 'members/member_form.html'
    success_url = reverse_lazy('members:member_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['tabs'] = ["info", "contacto", "redes"]
        
        context['info_fields'] = [
            "first_name", "last_name_paterno", "last_name_materno", "apodo",
            "birth_date", "fallecimiento_date", "lugar_nacimiento", "foto_principal",
            "estudios", "ocupacion", "relationship",
            "padre", "madre", "conyuge",
            "padrino_de_bautismo", "madrina_de_bautismo",
        ]
        context['contacto_fields'] = [
            "correomail", "phone_number", "address"
        ]
        context['redes_fields'] = [
            "whatsapp", "facebook", "linkedin", "instagram"
        ]
        return context


class MemberUpdateView(UpdateView):
    model = Member
    form_class = MemberForm
    template_name = 'members/member_form.html'
    success_url = reverse_lazy('members:member_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['tabs'] = ["info", "contacto", "redes"]
        
        context['info_fields'] = [
            "first_name", "last_name_paterno", "last_name_materno", "apodo",
            "birth_date", "fallecimiento_date", "lugar_nacimiento", "foto_principal",
            "estudios", "ocupacion", "relationship",
            "padre", "madre", "conyuge",
            "padrino_de_bautismo", "madrina_de_bautismo",
        ]
        context['contacto_fields'] = [
            "correomail", "phone_number", "address"
        ]
        context['redes_fields'] = [
            "whatsapp", "facebook", "linkedin", "instagram"
        ]
        return context

class MemberDetailView(DetailView):
    model = Member
    template_name = 'members/member_detail.html'
    context_object_name = 'member'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        member = self.object

        # Definir explícitamente los campos para la sección "Información General"
        # Estos son campos que no están en la cabecera (nombre, fechas) ni en las otras pestañas (contacto, redes)
        # y no son relaciones directas (padre, madre, cónyuge, hijos, hermanos, etc.)
        general_info_field_names = [
            'apodo',
            'lugar_nacimiento',
            'estudios',
            'ocupacion',
            # 'relationship' se maneja directamente en la plantilla con member.get_relationship_display
            # 'padrino_de_bautismo' y 'madrina_de_bautismo' se manejan directamente como valores
        ]
        
        context['general_info_fields'] = []
        for field_name in general_info_field_names:
            try:
                field = Member._meta.get_field(field_name)
                context['general_info_fields'].append(field)
            except models.FieldDoesNotExist:
                # Esto es útil si un campo en la lista no existe en el modelo
                print(f"Advertencia: El campo '{field_name}' no existe en el modelo Member.")


        # Pasar objetos de relaciones directas
        context['padre_obj'] = member.padre
        context['madre_obj'] = member.madre
        context['conyuge_obj'] = member.conyuge
        
        # Pasar campos para padrinos (estos son CharFields)
        context['padrino_bautismo_val'] = member.padrino_de_bautismo
        context['madrina_bautismo_val'] = member.madrina_de_bautismo

        # --- IMPORTANTE: Asegúrate de que estos métodos existan en tu modelo Member y devuelvan QuerySets ---
        # Por ejemplo, en tu models.py, deberías tener algo como:
        # class Member(models.Model):
        #     ...
        #     def hijos(self):
        #         return Member.objects.filter(Q(padre=self) | Q(madre=self))
        #     def hermanos(self):
        #         # Lógica para obtener hermanos (puede ser compleja si los padres no están registrados)
        #         if self.padre and self.madre:
        #             return Member.objects.filter(Q(padre=self.padre) | Q(madre=self.madre)).exclude(pk=self.pk)
        #         elif self.padre:
        #             return Member.objects.filter(padre=self.padre).exclude(pk=self.pk)
        #         elif self.madre:
        #             return Member.objects.filter(madre=self.madre).exclude(pk=self.pk)
        #         return Member.objects.none()
        #     def nietos(self):
        #         # Obtener hijos de los hijos
        #         hijos_pks = [hijo.pk for hijo in self.hijos()]
        #         return Member.objects.filter(Q(padre__in=hijos_pks) | Q(madre__in=hijos_pks))
        #     # Y así sucesivamente para bisnietos, tataranietos, choznos
        # ----------------------------------------------------------------------------------------------------

        context['hijos'] = member.hijos().all()
        context['hermanos'] = member.hermanos().all()
        context['nietos'] = member.nietos().all() 
        context['bisnietos'] = member.bisnietos().all()
        context['tataranietos'] = member.tataranietos().all()
        context['choznos'] = member.choznos().all()

        # --- Datos del árbol para d3.js - Versión revisada para incluir fechas y evitar bucles ---

        # Helper function para construir un nodo para el árbol, incluyendo datos de fecha
        def build_tree_node(member_obj, visited_pks):
            if member_obj is None or member_obj.pk in visited_pks:
                return None
            
            visited_pks.add(member_obj.pk)

            node_data = {
                'name': f"{member_obj.first_name or ''} {member_obj.last_name_paterno or ''}".strip(),
                'id': member_obj.pk,
                'birth_date': member_obj.birth_date.strftime("%d-%m-%Y") if member_obj.birth_date else '',
                'fallecimiento_date': member_obj.fallecimiento_date.strftime("%d-%m-%Y") if member_obj.fallecimiento_date else '',
                'is_current': member_obj.pk == member.pk, # Para destacar al miembro actual
                'children': []
            }

            # Recursivamente añadir solo los hijos directos
            for child in member_obj.hijos().all():
                child_subtree = build_tree_node(child, visited_pks)
                if child_subtree:
                    node_data['children'].append(child_subtree)
            
            return node_data

        # Inicializar el conjunto de PKS visitadas para la construcción del árbol
        global_visited_pks = set()
        
        # Construir el nodo raíz para el miembro actual
        root_node_for_tree = build_tree_node(member, global_visited_pks)
        
        if root_node_for_tree: # Asegurarse de que el nodo principal se construyó
            # Añadir Padres como una rama separada si existen
            parents_group_children = []
            if member.padre and member.padre.pk not in global_visited_pks:
                parents_group_children.append(build_tree_node(member.padre, global_visited_pks))
            if member.madre and member.madre.pk not in global_visited_pks:
                parents_group_children.append(build_tree_node(member.madre, global_visited_pks))
            
            valid_parents = [p for p in parents_group_children if p is not None]
            if valid_parents:
                # Crear un nodo ficticio 'Padres' para agrupar
                root_node_for_tree['children'].insert(0, {'name': 'Padres', 'id': 'parents_group', 'children': valid_parents})

            # Añadir Cónyuge como una rama separada si existe
            if member.conyuge and member.conyuge.pk not in global_visited_pks:
                spouse_node = build_tree_node(member.conyuge, global_visited_pks)
                if spouse_node:
                    spouse_node['name'] += ' (Cónyuge)'
                    root_node_for_tree['children'].insert(0, spouse_node) # Insertar al principio o según preferencia

        context['tree_data'] = json.dumps(root_node_for_tree) if root_node_for_tree else '{}'

        return context


class MemberDeleteView(DeleteView):
    model = Member
    template_name = 'members/member_confirm_delete.html'
    success_url = reverse_lazy('members:member_list')


# Esta vista es para el árbol genealógico general, no el árbol del detalle de un miembro individual.
def family_tree_view(request):
    members = Member.objects.all()

    def build_tree_from_root(member_obj, visited_pks):
        if not member_obj or member_obj.pk in visited_pks:
            return None
        visited_pks.add(member_obj.pk)

        node = {
            'name': f"{member_obj.first_name or ''} {member_obj.last_name_paterno or ''}".strip(),
            'id': member_obj.pk,
            'birth_date': member_obj.birth_date.strftime("%d-%m-%Y") if member_obj.birth_date else '',
            'fallecimiento_date': member_obj.fallecimiento_date.strftime("%d-%m-%Y") if member_obj.fallecimiento_date else '',
            'children': []
        }

        # Añadir cónyuge si existe y no ha sido visitado para evitar bucles o duplicados
        # Nota: para un d3.tree, añadir cónyuges como 'hijos' no es el modelo más adecuado
        # para un gráfico de árbol estricto. Un 'graph' (d3-force) sería mejor para relaciones complejas.
        if member_obj.conyuge and member_obj.conyuge.pk not in visited_pks:
            # Aquí se puede añadir el cónyuge como un 'hermano' o un nodo 'conyugal' en el mismo nivel,
            # pero para el modelo actual de d3.tree lo añadimos como hijo para que se visualice.
            node['children'].append({
                'name': f"{member_obj.conyuge.first_name or ''} {member_obj.conyuge.last_name_paterno or ''} (Cónyuge)".strip(),
                'id': member_obj.conyuge.pk,
                'birth_date': member_obj.conyuge.birth_date.strftime("%d-%m-%Y") if member_obj.conyuge.birth_date else '',
                'fallecimiento_date': member_obj.conyuge.fallecimiento_date.strftime("%d-%m-%Y") if member_obj.conyuge.fallecimiento_date else '',
            })
            visited_pks.add(member_obj.conyuge.pk) # Marcar cónyuge como visitado

        # Recursivamente añadir hijos y sus descendientes
        hijos = member_obj.hijos().all() # Asegúrate de que member_obj.hijos() existe
        for hijo in hijos:
            child_subtree = build_tree_from_root(hijo, visited_pks)
            if child_subtree:
                node['children'].append(child_subtree)
        
        return node

    # Encuentra miembros que son "raíces" (no tienen padres registrados en el sistema)
    def find_roots():
        all_members = Member.objects.all()
        
        # Identificar todos los miembros que son hijos de alguien en la base de datos
        children_pks = set()
        for m in all_members:
            if m.padre:
                children_pks.add(m.pk)
            if m.madre:
                children_pks.add(m.pk)
        
        # Las raíces son miembros que no están en el conjunto `children_pks`
        roots = [m for m in all_members if m.pk not in children_pks]
        
        # Alternativa: si no hay raíces claras (ej. todos los miembros tienen padres pero algunos padres faltan de la DB),
        # o si la base de datos está vacía, devuelve el miembro más antiguo como punto de partida.
        if not roots and all_members.exists():
            return [all_members.order_by('birth_date').first()] if all_members.filter(birth_date__isnull=False).exists() else [all_members.first()]
            
        return roots


    full_tree_data = []
    visited_for_full_tree = set()
    
    # Obtener todas las raíces y construir un árbol para cada una
    roots_to_process = find_roots()
        
    for root_member in roots_to_process:
        # Solo construir un subárbol si la raíz no ha sido visitada aún
        if root_member.pk not in visited_for_full_tree:
            subtree = build_tree_from_root(root_member, visited_for_full_tree)
            if subtree:
                full_tree_data.append(subtree)
    
    # Si después de procesar todas las raíces identificadas, aún tenemos miembros no visitados,
    # significa que hay segmentos desconectados. Intentar construir árboles para ellos también.
    # Esto ayuda a visualizar datos fragmentados.
    if members.exists(): # Solo si hay miembros en la DB
        for member_obj in members:
            if member_obj.pk not in visited_for_full_tree:
                subtree = build_tree_from_root(member_obj, visited_for_full_tree)
                if subtree:
                    full_tree_data.append(subtree)
        
    context = {
        'tree_data': json.dumps(full_tree_data),
        'members': members,
    }
    return render(request, 'members/family_tree.html', context)


def members_by_family_branch_view(request):
    members = Member.objects.all().order_by('last_name_paterno', 'last_name_materno', 'first_name')
    family_branches = {}

    for member in members:
        # Define the branch key based on paternal and maternal surnames
        paterno = (member.last_name_paterno or '').strip()
        materno = (member.last_name_materno or '').strip()

        branch_key = ""
        if paterno and materno:
            branch_key = f"{paterno} {materno}"
        elif paterno:
            branch_key = paterno
        elif materno: # Only if paterno is empty
            branch_key = materno
        else: # No surnames at all
            branch_key = "Sin Apellido"

        if branch_key not in family_branches:
            family_branches[branch_key] = []
        family_branches[branch_key].append(member)

    # Sort the family branches by their keys (surnames)
    # Convert to a list of (key, value) tuples for easy iteration in template
    sorted_branches = sorted(family_branches.items())

    context = {
        'sorted_branches': sorted_branches,
    }
    return render(request, 'members/members_by_family_branch.html', context)

# La función 'editar_miembro' ha sido eliminada ya que 'MemberUpdateView' cumple la misma función.