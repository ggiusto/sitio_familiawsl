# stories/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Story
from .forms import StoryForm

@login_required
def story_list(request):
    stories = Story.objects.all()
    context = {'stories': stories, 'title': 'Historias Familiares'}
    return render(request, 'stories/story_list.html', context)

@login_required
def story_create(request):
    if request.method == 'POST':
        form = StoryForm(request.POST)
        if form.is_valid():
            story = form.save(commit=False) # No guarda aún para asignar el autor
            story.author = request.user # Asigna el usuario logueado como autor
            story.save()
            messages.success(request, 'Historia añadida exitosamente.')
            return redirect('story_list')
    else:
        form = StoryForm()
    context = {'form': form, 'title': 'Añadir Nueva Historia'}
    return render(request, 'stories/story_form.html', context)

@login_required
def story_detail(request, pk):
    story = get_object_or_404(Story, pk=pk)
    context = {'story': story, 'title': f'Historia: {story.title}'}
    return render(request, 'stories/story_detail.html', context)

@login_required
def story_update(request, pk):
    story = get_object_or_404(Story, pk=pk)
    # Solo el autor o un superusuario pueden editar
    if request.user != story.author and not request.user.is_superuser:
        messages.error(request, 'No tienes permiso para editar esta historia.')
        return redirect('story_detail', pk=story.pk)

    if request.method == 'POST':
        form = StoryForm(request.POST, instance=story)
        if form.is_valid():
            form.save()
            messages.success(request, 'Historia actualizada exitosamente.')
            return redirect('story_detail', pk=story.pk)
    else:
        form = StoryForm(instance=story)
    context = {'form': form, 'title': f'Editar Historia: {story.title}'}
    return render(request, 'stories/story_form.html', context)

@login_required
def story_delete(request, pk):
    story = get_object_or_404(Story, pk=pk)
    # Solo el autor o un superusuario pueden eliminar
    if request.user != story.author and not request.user.is_superuser:
        messages.error(request, 'No tienes permiso para eliminar esta historia.')
        return redirect('story_detail', pk=story.pk)

    if request.method == 'POST':
        story.delete()
        messages.info(request, 'Historia eliminada exitosamente.')
        return redirect('story_list')
    context = {'story': story, 'title': f'Eliminar Historia: {story.title}'}
    return render(request, 'stories/story_confirm_delete.html', context)
