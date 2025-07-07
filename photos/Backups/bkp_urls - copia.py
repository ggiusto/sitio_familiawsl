from django.urls import path
from . import views

app_name = 'photos'

urlpatterns = [
    path('', views.photo_list, name='photo_list'),
    path('subir/', views.photo_upload, name='photo_upload'),
    path('<int:pk>/', views.photo_detail, name='photo_detail'),
]
