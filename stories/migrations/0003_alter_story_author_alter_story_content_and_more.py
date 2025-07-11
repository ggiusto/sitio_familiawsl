# Generated by Django 5.0.1 on 2025-06-05 23:10

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stories', '0002_alter_story_options_remove_story_autor_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='story',
            name='author',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Autor'),
        ),
        migrations.AlterField(
            model_name='story',
            name='content',
            field=models.TextField(verbose_name='Contenido de la Historia'),
        ),
        migrations.AlterField(
            model_name='story',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name='Fecha de Creación'),
        ),
        migrations.AlterField(
            model_name='story',
            name='updated_at',
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name='Última Actualización'),
        ),
    ]
