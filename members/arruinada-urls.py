from django.urls import path
from . import views

app_name = 'members'

urlpatterns = [
    path('', views.member_list, name='member_list'),
    path('crear/', views.MemberCreateView.as_view(), name='member_create'),
    path('<int:pk>/', views.member_detail, name='member_detail'),
    path('<int:pk>/eliminar/', views.MemberDeleteView.as_view(), name='member_delete'),
    path('<int:pk>/editar/', views.MemberUpdateView.as_view(), name='member_update'),
    
    # Rutas de Funciones Auxiliares
    path('ramas/', views.members_by_family_branch_view, name='family_branches'),
    path('fechas/', views.member_dates_query_view, name='member_dates'),
    path('exportar/excel/', views.export_members_excel, name='export_excel'),
    path('<int:pk>/exportar-pdf/', views.export_member_pdf, name='export_pdf'),
    
    # JSON y AJAX
    path('api/tree-data/<int:member_id>/', views.member_tree_data, name='member_tree_data'),
    # path('api/validate-dni/', views.validate_dni_ajax, name='validate_dni'),
    ]