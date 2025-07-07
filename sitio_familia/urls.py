from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from .views import HomeView, search_view  # ✅ Importación directa de search_view
from photos.views import photo_list
from stories.views import story_list

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', HomeView.as_view(), name='home'),  # ✅ Usamos HomeView, ya importado
    path('accounts/', include('django.contrib.auth.urls')),
    path('historias/', include('stories.urls')),
    path('fotos/', include('photos.urls')),
    path('members/', include(('members.urls', 'members'), namespace='members')),
    path('usuarios/', include('users.urls')),
    path('buscar/', search_view, name='search'),  # ✅ Corrección aquí
]

# Servir archivos multimedia en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

