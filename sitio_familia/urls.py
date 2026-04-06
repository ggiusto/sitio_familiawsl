from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Importaciones de vistas generales
from .views import HomeView, search_view 

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', HomeView.as_view(), name='home'),
    
    # Autenticación y Usuarios
    path('accounts/', include('django.contrib.auth.urls')),
    path('usuarios/', include('users.urls')),
    
    # Aplicaciones del Proyecto
    path('members/', include('members.urls')),
    path('historias/', include('stories.urls')),
    path('fotos/', include('photos.urls')), # Se eliminó la duplicación y el namespace manual
    
    # Búsqueda
    path('buscar/', search_view, name='search'),
]

# Servir archivos multimedia en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)