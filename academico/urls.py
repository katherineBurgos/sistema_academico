from django.urls import path

from . import views

app_name = "academico"

urlpatterns = [
    path("", views.InicioView.as_view(), name="inicio"),
    path("<slug:modelo>/", views.RecursoListView.as_view(), name="lista"),
    path("<slug:modelo>/crear/", views.RecursoCreateView.as_view(), name="crear"),
    path("<slug:modelo>/<int:pk>/pdf/", views.RecursoPdfView.as_view(), name="recurso_pdf"),
    path("<slug:modelo>/<int:pk>/editar/", views.RecursoUpdateView.as_view(), name="editar"),
    path("<slug:modelo>/<int:pk>/eliminar/", views.RecursoDeleteView.as_view(), name="eliminar"),
    path("<slug:modelo>/<int:pk>/", views.RecursoDetailView.as_view(), name="detalle"),
]
