from django.contrib import admin
from .models import Photo

@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'uploaded_by', 'uploaded_at')
    search_fields = ('title', 'description', 'uploaded_by__username')
    list_filter = ('uploaded_at', 'uploaded_by')

# Register your models here.
