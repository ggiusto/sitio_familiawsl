from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import now  # Importación necesaria

class Photo(models.Model):
    title = models.CharField(max_length=200, blank=True, null=True, verbose_name="Título (Opcional)")
    image = models.ImageField(upload_to='photos/', verbose_name="Imagen")
    description = models.TextField(blank=True, null=True, verbose_name="Descripción/Comentario")
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Subido por")
    uploaded_at = models.DateTimeField(default=now, verbose_name="Fecha de Subida")  # Corregido

    def __str__(self):
        return self.title if self.title else f"Foto {self.pk}"

    class Meta:
        verbose_name = "Foto Familiar"
        verbose_name_plural = "Fotos Familiares"
        ordering = ['-uploaded_at']