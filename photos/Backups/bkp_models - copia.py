from django.db import models
from django.conf import settings

class Photo(models.Model):
    imagen = models.ImageField(upload_to='photos/')  # carpeta media/photos/
    titulo = models.CharField(max_length=100, null=True, blank=True)
    descripcion = models.TextField(null=True, blank=True)
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    fecha_subida = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titulo if self.titulo else f"Foto {self.pk}"
