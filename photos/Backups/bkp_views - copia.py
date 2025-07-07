from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from .models import Photo
from .forms import PhotoForm

@login_required
def photo_list(request):
    fotos = Photo.objects.order_by('-fecha_subida')
    return render(request, 'photos/photo_list.html', {'fotos': fotos})

@login_required
@permission_required('photos.add_photo', raise_exception=True)
def photo_upload(request):
    if request.method == 'POST':
        form = PhotoForm(request.POST, request.FILES)
        if form.is_valid():
            foto = form.save(commit=False)
            foto.autor = request.user
            foto.save()
            return redirect('photos:photo_list')
    else:
        form = PhotoForm()
    return render(request, 'photos/photo_upload.html', {'form': form})

@login_required
def photo_detail(request, pk):
    foto = get_object_or_404(Photo, pk=pk)
    return render(request, 'photos/photo_detail.html', {'foto': foto})
