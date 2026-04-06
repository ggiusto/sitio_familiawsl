from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Q
from datetime import date
from django.urls import reverse
from django.core.files import File
from django.conf import settings

# Librerías para el código QR
import qrcode
from io import BytesIO
from PIL import Image

# Relaciones ordenadas desde el ancestro más antiguo hacia los descendientes
RELATIONSHIP_CHOICES = [
    ('TATARABUELO', '1ra Generación (Tatarabuelo/a)'),
    ('BISABUELO', '2da Generación (Bisabuelo/a)'),
    ('ABUELO', '3ra Generación (Abuelo/a)'),
    ('PADRE_MADRE', '4ta Generación (Padre/Madre)'),
    ('HIJO_HIJA', '5ta Generación (Hijo/a)'),
    ('NIETO_NIETA', '6ta Generación (Nieto/a)'),
    ('BISNIETO', '7ma Generación (Bisnieto/a)'),
    ('TATARANIETO', '8va Generación (Tataranieto/a)'),
    ('CHOZNO', '9na Generación (Chozno/a)'),
    ('HERMANO', 'Hermano/a'),
    ('TIO', 'Tío/a'),
    ('PRIMO', 'Primo/a'),
    ('CONYUGE', 'Cónyuge'),
]

class Member(models.Model):
    # --- DATOS PERSONALES ---
    first_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Nombres"
    )
    last_name_paterno = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Apellido Paterno"
    )
    last_name_materno = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Apellido Materno"
    )
    apodo = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Apodo"
    )
    dni = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="DNI/Pasaporte"
    )
    birth_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha de Nacimiento"
    )
    death_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha de Fallecimiento"
    )
    lugar_nacimiento = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Lugar de Nacimiento"
    )
    lugar_residencia = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Lugar de Residencia"
    )
    ocupacion = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Ocupación/Profesión"
    )
    email = models.EmailField(
        blank=True,
        null=True,
        verbose_name="Correo Electrónico"
    )
    telefono = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Teléfono/WhatsApp"
    )
    biografia = models.TextField(
        blank=True,
        null=True,
        verbose_name="Biografía/Notas Históricas"
    )

    # --- ARCHIVOS MULTIMEDIA ---
    foto_principal = models.ImageField(
        upload_to='members/photos/',
        blank=True,
        null=True,
        verbose_name="Foto de Perfil"
    )
    qr_code = models.ImageField(
        upload_to='members/qrcodes/',
        blank=True,
        null=True,
        editable=False
    )

    # --- RELACIONES FAMILIARES ---
    relationship = models.CharField(
        max_length=20,
        choices=RELATIONSHIP_CHOICES,
        blank=True,
        null=True,
        verbose_name="Parentesco Principal"
    )
    padre = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='hijos_padre'
    )
    madre = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='hijos_madre'
    )
    conyuge = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='pareja'
    )

    # --- PROPIEDADES Y MÉTODOS ---

    @property
    def edad(self):
        """Cálculo dinámico de edad (al día de hoy o al fallecer)"""
        if not self.birth_date:
            return None
        end_date = self.death_date if self.death_date else date.today()
        return end_date.year - self.birth_date.year - (
            (end_date.month, end_date.day) < (self.birth_date.month, self.birth_date.day)
        )

    @property
    def edad_label(self):
        """Devuelve la etiqueta correcta según el estado del familiar"""
        if self.death_date:
            return "Edad al fallecer"
        return "Edad actual"

    def get_siblings(self):
        """Busca hermanos (comparten padre o madre)"""
        filters = Q()
        if self.padre:
            filters |= Q(padre=self.padre)
        if self.madre:
            filters |= Q(madre=self.madre)
        if not filters:
            return Member.objects.none()
        return Member.objects.filter(filters).exclude(pk=self.pk).distinct()

    def clean(self):
        """Validaciones de integridad de fechas"""
        if self.birth_date and self.death_date:
            if self.death_date < self.birth_date:
                raise ValidationError("La fecha de fallecimiento no puede ser anterior al nacimiento.")

    def save(self, *args, **kwargs):
        """Sobrescribe save para generar el QR automáticamente"""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Generamos QR si es nuevo o si no tiene uno asignado aún
        if is_new or not self.qr_code:
            self.generate_qr()

    def generate_qr(self):
        """Genera un código QR que apunta al detalle del miembro"""
        base_url = "https://familia.gusbidart.org"
        try:
            detail_url = reverse('members:member_detail', args=[self.pk])
            full_url = f"{base_url}{detail_url}"
        except:
            # Fallback en caso de que la URL reversa falle durante migraciones iniciales
            full_url = f"{base_url}/members/{self.pk}/"

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(full_url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        filename = f'qr-{self.pk}-{self.last_name_paterno or "sin-apellido"}.png'
        
        # Guardamos el archivo sin disparar save() de nuevo (save=False)
        self.qr_code.save(filename, File(buffer), save=False)
        
        # Actualización directa en la DB para evitar recursión infinita
        Member.objects.filter(pk=self.pk).update(qr_code=self.qr_code.name)

    def __str__(self):
        nombre = self.first_name or ''
        apellido_paterno = self.last_name_paterno or ''
        apellido_materno = self.last_name_materno or ''
        
        full_name_parts = [part for part in [nombre, apellido_paterno, apellido_materno] if part]
        full_name = " ".join(full_name_parts)
        
        relacion = self.get_relationship_display() if self.relationship else ''
        
        if full_name and relacion:
            return f"{full_name} ({relacion})"
        return full_name or f"Miembro {self.pk}"

    class Meta:
        verbose_name = "Miembro de la Familia"
        verbose_name_plural = "Miembros de la Familia"
        ordering = ['last_name_paterno', 'first_name']