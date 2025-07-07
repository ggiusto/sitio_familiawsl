# members/urls.py
from django.urls import path
from .views import (
    MemberListView,
    MemberDetailView,
    MemberCreateView,
    MemberUpdateView,
    MemberDeleteView,
    family_tree_view,
    members_by_family_branch_view, # ADDED: Import new view
)

app_name = 'members'

urlpatterns = [
    path('', MemberListView.as_view(), name='member_list'),
    path('crear/', MemberCreateView.as_view(), name='member_create'),
    path('<int:pk>/', MemberDetailView.as_view(), name='member_detail'),
    path('<int:pk>/editar/', MemberUpdateView.as_view(), name='member_update'),
    path('<int:pk>/eliminar/', MemberDeleteView.as_view(), name='member_delete'),
    path('arbol/', family_tree_view, name='family_tree'),
    path('ramas/', members_by_family_branch_view, name='family_branches'), # ADDED: New URL
]