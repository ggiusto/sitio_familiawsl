# Generated by Django 5.0.1 on 2025-06-03 15:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='member',
            name='foto',
        ),
        migrations.AddField(
            model_name='member',
            name='foto_perfil',
            field=models.ImageField(blank=True, null=True, upload_to='profile_photos/'),
        ),
    ]
