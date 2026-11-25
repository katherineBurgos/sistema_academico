from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, path
from django.views.generic import RedirectView
from core.views import RegistroView

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="academico:inicio", permanent=False)),
    path("admin/", admin.site.urls),
    path("login/", LoginView.as_view(), name="login"),
    path("registro/", RegistroView.as_view(), name="registro"),
    path("logout/", LogoutView.as_view(), name="logout"),      # solo acepta POST
    path("academico/", include("academico.urls")),
]

if settings.DEBUG:                                              # sirve las fotos subidas en desarrollo
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
