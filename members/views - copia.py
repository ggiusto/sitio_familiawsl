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
            "estudios", "ocupación", "relationship",
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
            "estudios", "ocupación", "relationship",
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

        # Dynamically get all non-relational fields for display in "Datos Personales"
        excluded_from_general_info = [
            'id', 'foto_principal', # Handled explicitly for display
            'padre', 'madre', 'conyuge', # Handled explicitly as related objects
            'padrino_de_bautismo', 'madrina_de_bautismo', # Handled explicitly as family string fields
            'correomail', 'phone_number', 'address', # Handled in contact section
            'whatsapp', 'facebook', 'linkedin', "instabram", # Handled in social media section
            'birth_date', 'fallecimiento_date', # Handled explicitly in header (birth and death date)
            'first_name', 'last_name_paterno', 'last_name_materno', # Handled explicitly in header
        ]
        
        context['general_info_fields'] = []
        for field in Member._meta.fields:
            # Check if it's not a ForeignKey, ManyToManyField, or explicitly excluded
            if field.name not in excluded_from_general_info and not isinstance(field, (models.ForeignKey, models.ManyToManyField)):
                context['general_info_fields'].append(field)
        
        # Pass specific related members for explicit display
        context['padre_obj'] = member.padre
        context['madre_obj'] = member.madre
        context['conyuge_obj'] = member.conyuge
        
        # Pass fields for baptism godparents (these are CharFields)
        context['padrino_bautismo_val'] = member.padrino_de_bautismo
        context['madrina_bautismo_val'] = member.madrina_de_bautismo

        # Pass related children, siblings, and deeper generations
        context['hijos'] = member.hijos().all()
        context['hermanos'] = member.hermanos().all()
        context['nietos'] = member.nietos().all() # Get grandchildren
        context['bisnietos'] = member.bisnietos().all() # ADDED: Get bisnietos
        context['tataranietos'] = member.tataranietos().all() # ADDED: Get tataranietos
        context['choznos'] = member.choznos().all() # ADDED: Get choznos

        # --- Tree data for d3.js - Revised recursive building ---

        # Helper function to build a node for the tree, only including its direct children (descendants)
        # This function should NOT add 'Padres' or 'Cónyuge' nodes, as those are handled at the top level for the 'member'.
        def build_descendant_tree_node(member_obj, visited_pks):
            if member_obj is None or member_obj.pk in visited_pks:
                return None
            
            visited_pks.add(member_obj.pk)

            node_data = {
                'name': f"{member_obj.first_name or ''} {member_obj.last_name_paterno or ''}".strip(),
                'id': member_obj.pk,
                'children': []
            }

            # Recursively add only direct children (descendants)
            for child in member_obj.hijos().all():
                child_subtree = build_descendant_tree_node(child, visited_pks)
                if child_subtree:
                    node_data['children'].append(child_subtree)
            
            return node_data

        # Initialize the main member's node for the D3 tree
        # Use a single visited set for the entire tree building process to prevent loops
        global_visited_pks = set() 
        root_node_for_tree = {
            'name': f"{member.first_name or ''} {member.last_name_paterno or ''} {member.last_name_materno or ''}".strip(),
            'id': member.pk,
            'children': []
        }
        global_visited_pks.add(member.pk) # Mark the root member as visited

        # Add Parents branch for the main member (if they exist)
        parents_group_children = []
        if member.padre and member.padre.pk not in global_visited_pks:
            parents_group_children.append(build_descendant_tree_node(member.padre, global_visited_pks))
        if member.madre and member.madre.pk not in global_visited_pks:
            parents_group_children.append(build_descendant_tree_node(member.madre, global_visited_pks))
        
        valid_parents = [p for p in parents_group_children if p is not None]
        if valid_parents:
            root_node_for_tree['children'].append({'name': 'Padres', 'children': valid_parents})

        # Add Spouse for the main member (if exists)
        if member.conyuge and member.conyuge.pk not in global_visited_pks:
            spouse_node = build_descendant_tree_node(member.conyuge, global_visited_pks)
            if spouse_node:
                spouse_node['name'] += ' (Cónyuge)'
                root_node_for_tree['children'].append(spouse_node)

        # Add Hijos branch (actual children of the root member)
        children_nodes_for_root = []
        for child in member.hijos().all():
            child_subtree = build_descendant_tree_node(child, global_visited_pks)
            if child_subtree:
                children_nodes_for_root.append(child_subtree)
        
        if children_nodes_for_root:
            # Append children directly to the root member's children list
            # No intermediate "Hijos" grouping node here for the main member's direct children
            root_node_for_tree['children'].extend(children_nodes_for_root)

        context['tree_data'] = json.dumps(root_node_for_tree) if root_node_for_tree else '{}'

        return context


class MemberDeleteView(DeleteView):
    model = Member
    template_name = 'members/member_confirm_delete.html'
    success_url = reverse_lazy('members:member_list')

# This view is for the general family tree, not the individual member detail tree.
def family_tree_view(request):
    members = Member.objects.all()

    def build_tree_from_root(member, visited):
        if not member or member.pk in visited:
            return None
        visited.add(member.pk)

        node = {
            'name': f"{member.first_name or ''} {member.last_name_paterno or ''}".strip(),
            'id': member.pk, # Add ID for potential linking
            'children': []
        }

        # Add spouse if exists and not already visited
        if member.conyuge and member.conyuge.pk not in visited:
            node['children'].append({
                'name': f"{member.conyuge.first_name or ''} {member.conyuge.last_name_paterno or ''} (Cónyuge)".strip(),
                'id': member.conyuge.pk,
            })

        # Recursively add children and their descendants
        hijos = member.hijos().all()
        for hijo in hijos:
            child_subtree = build_tree_from_root(hijo, visited)
            if child_subtree:
                node['children'].append(child_subtree)
        
        return node

    # Find members who are considered "roots" (have no parents within the system)
    def find_roots():
        all_members = Member.objects.all()
        
        # Identify all members who are children of someone in the database
        children_pks = set()
        for m in all_members:
            if m.padre:
                children_pks.add(m.pk)
            if m.madre:
                children_pks.add(m.pk)
        
        # Roots are members who are not found in the `children_pks` set
        roots = [m for m in all_members if m.pk not in children_pks]
        
        # Fallback: if no clear roots (e.g., all members have parents but some parents are missing from DB),
        # or if the database is empty, return an empty list or the first member.
        if not roots and all_members.exists():
            # If everyone has parents, it might indicate a fragmented tree or an issue.
            # As a last resort, return the oldest member by birth date as a starting point.
            return [all_members.order_by('birth_date').first()]
            
        return roots


    full_tree_data = []
    visited_for_full_tree = set()
    
    # Get all roots and build a tree for each
    roots_to_process = find_roots()
        
    for root_member in roots_to_process:
        # Only build a subtree if the root hasn't been visited yet (e.g., as part of another root's branch)
        if root_member.pk not in visited_for_full_tree:
            subtree = build_tree_from_root(root_member, visited_for_full_tree)
            if subtree:
                full_tree_data.append(subtree)
    
    # If after processing all identified roots, we still have unvisited members,
    # it means there are disconnected segments. Try to build trees for them too.
    if not full_tree_data and members.exists():
        # This block ensures we always attempt to generate some tree, even if relationships are sparse or fragmented.
        for member in members:
            if member.pk not in visited_for_full_tree:
                subtree = build_tree_from_root(member, visited_for_full_tree)
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


def editar_miembro(request, pk):
    miembro = get_object_or_404(Member, pk=pk)
    if request.method == 'POST':
        form = MemberForm(request.POST, instance=miembro)
        if form.is_valid():
            form.save()
            return redirect('miembros_lista')  # Cambia por el nombre correcto de tu vista de listado
    else:
        form = MemberForm(instance=miembro)
    return render(request, 'members/editar_miembro.html', {'form': form})