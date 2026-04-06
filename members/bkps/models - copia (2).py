from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Q # Importamos Q para consultas complejas

# Relaciones ordenadas desde el ancestro más antiguo hacia los descendientes
RELATIONSHIP_CHOICES = [
    ('TATARABUELO', '1ra Generación'),
    ('BISABUELO', '2da Generación'),
    ('ABUELO', '3ra Generación'),
    ('PADRE_MADRE', '4ta Generación'),
    ('HIJO_HIJA', '5ta Generación'),
    ('NIETO_NIETA', '6ta Generación'),
    ('BISNIETO', '7ma Generación'), # ADDED: Bisnieto relationship
    ('TATARANIETO', '8va Generación'), # ADDED: Tataranieto relationship
    ('CHOZNO', '9na Generación'), # ADDED: Chozno relationship
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
        verbose_name='Fecha de Nacimiento'
    )
    fallecimiento_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de Fallecimiento'
    )
    lugar_nacimiento = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Lugar de Nacimiento"
    )
    foto_principal = models.ImageField(
        upload_to='photos/',
        blank=True,
        null=True,
        verbose_name="Foto Principal"
    )
    estudios = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Estudios"
    )
    
    # CORRECCIÓN: Se define como 'ocupacion' (sin tilde) para compatibilidad interna de Django
    # pero manteniendo el verbose_name con tilde para la interfaz.
    ocupacion = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Ocupación"
    )
    
    relationship = models.CharField(
        max_length=50,
        choices=RELATIONSHIP_CHOICES,
        blank=True,
        null=True,
        verbose_name="Relación"
    )

    # Relaciones familiares
    padre = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        related_name='hijos_por_padre',
        blank=True,
        null=True,
        verbose_name="Padre"
    )
    madre = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        related_name='hijos_por_madre',
        blank=True,
        null=True,
        verbose_name="Madre"
    )
    conyuge = models.OneToOneField(
        'self',
        on_delete=models.SET_NULL,
        related_name='conyuge_de',
        blank=True,
        null=True,
        verbose_name="Cónyuge"
    )
    padrino_de_bautismo = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Padrino de Bautismo"
    )
    madrina_de_bautismo = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Madrina de Bautismo"
    )

    # Datos de contacto
    correomail = models.EmailField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Correo Electrónico"
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Número de Teléfono"
    )
    address = models.TextField(
        blank=True,
        null=True,
        verbose_name="Dirección"
    )

    # Redes sociales
    whatsapp = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="WhatsApp"
    )
    facebook = models.URLField(
        blank=True,
        null=True,
        verbose_name="Facebook"
    )
    linkedin = models.URLField(
        blank=True,
        null=True,
        verbose_name="LinkedIn"
    )
    instagram = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Instagram"
    )

    # --- Lógica de Relaciones (Tu código original) ---

    def hijos(self):
        return Member.objects.filter(Q(padre=self) | Q(madre=self))

    def nietos(self):
        all_nietos = Member.objects.none()
        for hijo in self.hijos().all():
            all_nietos |= hijo.hijos()
        return all_nietos.distinct()

    def bisnietos(self):
        all_bisnietos = Member.objects.none()
        for nieto in self.nietos().all():
            all_bisnietos |= nieto.hijos()
        return all_bisnietos.distinct()

    def tataranietos(self):
        all_tataranietos = Member.objects.none()
        for bisnieto in self.bisnietos().all():
            all_tataranietos |= bisnieto.hijos()
        return all_tataranietos.distinct()

    def choznos(self):
        all_choznos = Member.objects.none()
        for tataranieto in self.tataranietos().all():
            all_choznos |= tataranieto.hijos()
        return all_choznos.distinct()

    def hermanos(self):
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
        else:
            return f"Miembro #{self.id}"

    class Meta:
        verbose_name = "Miembro"
        verbose_name_plural = "Miembros"
        ordering = ['last_name_paterno', 'first_name']
    @property
    def edad(self):
        if not self.birth_date:
            return None
        
        # Si la persona ha fallecido, calculamos la edad a la fecha de fallecimiento
        # Si no, calculamos la edad a la fecha actual
        fecha_final = self.fallecimiento_date if self.fallecimiento_date else date.today()
        
        try:
            edad = fecha_final.year - self.birth_date.year - (
                (fecha_final.month, fecha_final.day) < (self.birth_date.month, self.birth_date.day)
            )
            return edad
        except Exception:
            return None