# =====================================================================
# core/mixins.py · componentes reutilizables
# (FiltroCamposMixin, ExportarMixin y ComprobantePdfMixin se agregan en la Unidad 4)
# =====================================================================


class UsuarioRegistroMixin:
    """Guarda quién registró o modificó el objeto. Va en Create y Update."""

    def form_valid(self, form):
        form.instance.user = self.request.user      # el usuario conectado
        return super().form_valid(form)
