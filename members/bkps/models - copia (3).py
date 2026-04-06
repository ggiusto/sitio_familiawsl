from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Q
from datetime import date
from django.urls import reverse
from django.core.files import File

# Librerías para el código QR
import qrcode
from io import BytesIO
from PIL import Image

# Relaciones ordenadas desde el ancestro más antiguo hacia los descendientes
RELATIONSHIP_CHOICES = [
    ('TATARABUELO', '1ra Generación'),
    ('BISABUELO', '2da Generación'),
    ('ABUELO', '3ra Generación'),
    ('PADRE_MADRE', '4ta Generación'),
    ('HIJO_HIJA', '5ta Generación'),
    ('NIETO_NIETA', '6ta Generación'),
    ('BISNIETO', '7ma Generación'),
    ('TATARANIETO', '8va Generación'),
    ('CHOZNO', '9na Generación'),
    ('HERMANO', 'Hermano/a'),
    ('TIO', 'Tío/a'),
    ('PRIMO', 'Primo/a'),
    ('CONYUGE', 'Cónyuge'),
]

class Member(models.Model):
    # Datos personales
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
    birth_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de Nacimiento"
    )
    fallecimiento_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de Fallecimiento"
    )
    lugar_nacimiento = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Lugar de Nacimiento"
    )
    foto_principal = models.ImageField(
        upload_to='members/',
        blank=True,
        null=True,
        verbose_name="Foto de Perfil"
    )
    
    # Campo para el Código QR
    qr_code = models.ImageField(
        upload_to='qr_codes/', 
        blank=True, 
        null=True,
        verbose_name="Código QR de Acceso"
    )

    # Información adicional
    estudios = models.TextField(blank=True, null=True, verbose_name="Estudios")
    ocupacion = models.TextField(blank=True, null=True, verbose_name="Ocupación/Oficio")
    
    # Datos de contacto
    correomail = models.EmailField(blank=True, null=True, verbose_name="Correo Electrónico")
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")
    address = models.CharField(max_length=255, blank=True, null=True, verbose_name="Dirección")

    # Redes sociales
    whatsapp = models.CharField(max_length=50, blank=True, null=True, verbose_name="WhatsApp")
    facebook = models.URLField(blank=True, null=True, verbose_name="Facebook")
    linkedin = models.URLField(blank=True, null=True, verbose_name="LinkedIn")
    instagram = models.CharField(max_length=100, blank=True, null=True, verbose_name="Instagram")

    # Relaciones familiares
    relationship = models.CharField(
    max_length=50,  # Aumentado de 20 a 50
    choices=RELATIONSHIP_CHOICES,
    blank=True,
    null=True,
    verbose_name="Generación/Relación"
    )    
    padre = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hijos_padre',
        verbose_name="Padre"
    )
    madre = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hijos_madre',
        verbose_name="Madre"
    )
    conyuge = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conyuge_de',
        verbose_name="Cónyuge"
    )
    
    # Padrinos
    padrino_de_bautismo = models.CharField(max_length=200, blank=True, null=True, verbose_name="Padrino de Bautismo")
    madrina_de_bautismo = models.CharField(max_length=200, blank=True, null=True, verbose_name="Madrina de Bautismo")

    @property
    def edad(self):
        if self.birth_date:
            today = date.today()
            return today.year - self.birth_date.year - (
                (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
            )
        return None

    def get_siblings(self):
        if not self.padre and not self.madre:
            return Member.objects.none()
        hermanos_qs = Member.objects.none()
        if self.padre:
            hermanos_qs = hermanos_qs | Member.objects.filter(padre=self.padre)
        if self.madre:
            hermanos_qs = hermanos_qs | Member.objects.filter(madre=self.madre)
        return hermanos_qs.exclude(pk=self.pk).distinct()

    def clean(self):
        if self.conyuge and self.conyuge == self:
            raise ValidationError("Un miembro no puede ser su propio cónyuge.")
        if self.padre and self.padre == self:
            raise ValidationError("Un miembro no puede ser su propio padre.")
        if self.madre and self.madre == self:
            raise ValidationError("Un miembro no puede ser su propia madre.")

    def save(self, *args, **kwargs):
        # 1. Guardado inicial para asegurar que el objeto tiene un ID (necesario para la URL)
        is_new = self.pk is None
        super().save(*args, **kwargs)

        # 2. Lógica de generación del Código QR
        # Construimos la URL del perfil. 
        # IMPORTANTE: Reemplaza 'http://127.0.0.1:8000' por tu dominio real en producción.
        domain = "http://127.0.0.1:8000" 
        path = reverse('members:member_detail', kwargs={'pk': self.pk})
        full_url = f"{domain}{path}"

        # Configuración del QR
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H, # Alta corrección por si se imprime pequeño
            box_size=10,
            border=4,
        )
        qr.add_data(full_url)
        qr.make(fit=True)

        # Crear la imagen
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Guardar la imagen en el campo qr_code
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        filename = f'qr-{self.pk}-{self.last_name_paterno}.png'
        
        # Usamos save=False para evitar recursión infinita en el save()
        self.qr_code.save(filename, File(buffer), save=False)
        
        # 3. Guardado final de los campos actualizados (específicamente el QR)
        super().save(update_fields=['qr_code'])

    def __str__(self):
        nombre = self.first_name or ''
        apellido_paterno = self.last_name_paterno or ''
        apellido_materno = self.last_name_materno or ''
        full_name_parts = [part for part in [nombre, apellido_paterno, apellido_materno] if part]
        full_name = " ".join(full_name_parts)
        relacion = self.get_relationship_display() if self.relationship else ''
        if full_name and relacion:
            return f"{full_name} ({relacion})"
        elif full_name:
            return full_name
        elif relacion:
            return f"Miembro ({relacion})"
        return f"Miembro {self.pk}"

    class Meta:
        verbose_name = "Miembro"
        verbose_name_plural = "Miembros"