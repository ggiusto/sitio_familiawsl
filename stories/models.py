# stories/models.py

from django.db import models
from django.contrib.auth.models import User # Importa el modelo de usuario de Django
from django.utils.timezone import now

class Story(models.Model):
    title = models.CharField(max_length=200, verbose_name="Título")
    content = models.TextField(verbose_name="Contenido de la Historia")
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Autor") # Relación con el usuario
    created_at = models.DateTimeField(default=now, verbose_name="Fecha de Creación")
    updated_at = models.DateTimeField(default=now, verbose_name="Última Actualización")

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Historia Familiar"
        verbose_name_plural = "Historias Familiares"
        ordering = ['-created_at'] # Ordena por fecha de creación descendente
