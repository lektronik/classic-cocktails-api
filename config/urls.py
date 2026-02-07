
from django.urls import path, include, re_path
from django.views.generic.base import RedirectView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [


    path('', include('drinks.urls')),
    re_path(r'^drinks/(?P<path>.*)$', RedirectView.as_view(url='/media/drinks/%(path)s', permanent=True)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
