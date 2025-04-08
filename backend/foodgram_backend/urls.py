from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from recipes.views import recipe_redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('r/<str:short_url>/', recipe_redirect, name='recipe_redirect'),
    path('api/', include(('api.urls', 'api'))),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )
