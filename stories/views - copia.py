from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from .models import Story
from .forms import StoryForm

@login_required
def story_list(request):
    historias = Story.objects.order_by('-fecha_creacion')
    return render(request, 'stories/story_list.html', {'historias': historias})

@login_required
@permission_required('stories.add_story', raise_exception=True)
def story_create(request):
    if request.method == 'POST':
        form = StoryForm(request.POST)
        if form.is_valid():
            historia = form.save(commit=False)
            historia.autor = request.user
            historia.save()
            return redirect('stories:story_list')
    else:
        form = StoryForm()
    return render(request, 'stories/story_create.html', {'form': form})

@login_required
def story_detail(request, pk):
    historia = get_object_or_404(Story, pk=pk)
    return render(request, 'stories/story_detail.html', {'historia': historia})
