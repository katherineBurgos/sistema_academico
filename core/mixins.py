from django.utils import timezone
from django.http import HttpResponseBadRequest

from .utils import exportar_excel, render_pdf, valor_campo


class UsuarioRegistroMixin:
    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class FiltroCamposMixin:
    filtro_form_class = None
    campos_disponibles = ()
    campos_por_defecto = ()

    def filtrar(self, queryset, datos):
        return queryset

    def get_filtro_form(self):
        return (
            self.filtro_form_class(self.request.GET or None)
            if self.filtro_form_class else None
        )

    def get_queryset(self):
        queryset = super().get_queryset()
        self.filtro_form = self.get_filtro_form()
        if self.filtro_form and self.filtro_form.is_valid():
            queryset = self.filtrar(queryset, self.filtro_form.cleaned_data)
        return queryset

    def get_campos_seleccionados(self):
        titulos = dict(self.campos_disponibles)
        elegidos = [
            campo for campo in self.request.GET.getlist("campos")
            if campo in titulos
        ]
        elegidos = elegidos or [
            campo for campo in self.campos_por_defecto if campo in titulos
        ] or list(titulos)
        return [(campo, titulos[campo]) for campo in elegidos]

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        campos = self.get_campos_seleccionados()
        contexto["filtro_form"] = self.filtro_form
        contexto["campos_disponibles"] = self.campos_disponibles
        contexto["campos_seleccionados"] = [campo for campo, _ in campos]
        contexto["encabezados"] = [titulo for _, titulo in campos]
        contexto["filas"] = [
            (objeto, [valor_campo(objeto, campo) for campo, _ in campos])
            for objeto in contexto["object_list"]
        ]
        consulta = self.request.GET.copy()
        consulta.pop("page", None)
        consulta.pop("exportar", None)
        contexto["consulta"] = consulta.urlencode()
        return contexto


class ExportarMixin(FiltroCamposMixin):
    titulo_reporte = "Reporte académico"
    nombre_archivo = "reporte"
    template_pdf_listado = "core/pdf/listado.html"

    def filtros_aplicados(self):
        if not self.filtro_form or not self.filtro_form.is_valid():
            return []
        filtros = []
        for nombre, valor in self.filtro_form.cleaned_data.items():
            if valor in (None, ""):
                continue
            campo = self.filtro_form.fields[nombre]
            if hasattr(valor, "_meta"):
                etiqueta = str(valor)
            elif hasattr(campo, "choices"):
                etiqueta = dict(campo.choices).get(valor, valor)
            else:
                etiqueta = valor
            filtros.append(f"{campo.label}: {etiqueta}")
        return filtros

    def get(self, request, *args, **kwargs):
        formato = request.GET.get("exportar")
        if formato not in {"excel", "pdf"}:
            return super().get(request, *args, **kwargs)

        queryset = self.get_queryset()
        if self.filtro_form and not self.filtro_form.is_valid():
            return HttpResponseBadRequest("Corrige los filtros antes de exportar.")
        campos = self.get_campos_seleccionados()
        encabezados = [titulo for _, titulo in campos]
        filas = [
            [valor_campo(objeto, ruta) for ruta, _ in campos]
            for objeto in queryset
        ]
        if formato == "excel":
            return exportar_excel(
                self.titulo_reporte,
                encabezados,
                filas,
                self.get_nombre_archivo(),
            )
        return render_pdf(
            self.template_pdf_listado,
            {
                "titulo": self.titulo_reporte,
                "fecha": timezone.localtime(),
                "usuario": request.user,
                "total": len(filas),
                "filtros": self.filtros_aplicados(),
                "encabezados": encabezados,
                "filas": filas,
            },
            self.get_nombre_archivo(),
        )

    def get_nombre_archivo(self):
        return self.nombre_archivo


class ComprobantePdfMixin:
    template_pdf = None
    nombre_archivo = "comprobante"

    def render_to_response(self, context, **response_kwargs):
        context["fecha"] = timezone.localtime()
        context["usuario"] = self.request.user
        return render_pdf(
            self.template_pdf,
            context,
            f"{self.get_nombre_archivo()}-{self.object.pk}",
        )

    def get_nombre_archivo(self):
        return self.nombre_archivo
