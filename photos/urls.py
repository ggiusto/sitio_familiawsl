# photos/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.photo_list, name='photo_list'),
    path('upload/', views.photo_upload, name='photo_upload'),
    path('<int:pk>/', views.photo_detail, name='photo_detail'),
    path('<int:pk>/edit/', views.photo_update, name='photo_update'),
    path('<int:pk>/delete/', views.photo_delete, name='photo_delete'),
]
