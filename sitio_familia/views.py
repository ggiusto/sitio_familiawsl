from django.shortcuts import render
from django.views.generic import TemplateView
from members.models import Member
from stories.models import Story
from photos.models import Photo
from django.db.models import Q

def search_view(request):
    query = request.GET.get('q')
    results = []
    story_results = []
    photo_results = []

    if query:
        results = Member.objects.filter(
            Q(first_name__icontains=query) |
            Q(last_name_paterno__icontains=query) |
            Q(last_name_materno__icontains=query) |
            Q(apodo__icontains=query)
        )

        story_results = Story.objects.filter(
            Q(title__icontains=query) |
            Q(content__icontains=query)
        )

        photo_results = Photo.objects.filter(
            Q(description__icontains=query)
        )

    context = {
        'query': query,
        'results': results,
        'stories': story_results,
        'photos': photo_results,
    }
    return render(request, 'search_results.html', context)

def home_view(request):
    return render(request, 'index.html')

class HomeView(TemplateView):
    template_name = "index.html"
