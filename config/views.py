from django.shortcuts import render


def home_view(request):
    return render(request, 'home.html')


def about_view(request):
    return render(request, 'about.html')


def custom_404_view(request, exception=None):
    return render(request, '404.html', status=404)


def custom_500_view(request):
    return render(request, '500.html', status=500)
