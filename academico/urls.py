from django.urls import path

from . import views

app_name = "academico"

urlpatterns = [
    path("", views.InicioView.as_view(), name="inicio"),
    path("<slug:modelo>/", views.lista_modelo, name="lista"),
    path("<slug:modelo>/crear/", views.formulario_modelo, name="crear"),
    path("<slug:modelo>/<int:pk>/editar/", views.formulario_modelo, name="editar"),
    path("<slug:modelo>/<int:pk>/eliminar/", views.eliminar_modelo, name="eliminar"),
]
