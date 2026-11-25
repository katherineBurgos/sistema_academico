# =====================================================================
# core/models.py · el molde que heredan TODOS los modelos del sistema
# =====================================================================
from django.contrib.auth.models import User
from django.db import models


class ModeloBase(models.Model):
    user = models.ForeignKey(                    # quién registró o modificó por última vez
        User, on_delete=models.SET_NULL, null=True, blank=True, editable=False,
        related_name="%(app_label)s_%(class)s_registrados",   # nombre de vuelta único por modelo
        verbose_name="Registrado por",
    )
    fecha_creacion = models.DateTimeField("Fecha de creación", auto_now_add=True)
    fecha_modificacion = models.DateTimeField("Última modificación", auto_now=True)

    class Meta:
        abstract = True                          # molde: no crea tabla
