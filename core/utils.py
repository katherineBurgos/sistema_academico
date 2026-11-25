import logging
from io import BytesIO
from pathlib import Path
from urllib.parse import unquote, urlsplit

from django.conf import settings
from django.contrib.staticfiles import finders
from django.http import HttpResponse
from django.template.loader import render_to_string
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill


logger = logging.getLogger(__name__)


def valor_campo(objeto, ruta):
    """Obtiene un valor siguiendo una ruta de atributos separada por __."""
    for parte in ruta.split("__"):
        if objeto is None:
            return ""
        mostrar = getattr(objeto, f"get_{parte}_display", None)
        try:
            objeto = mostrar() if callable(mostrar) else getattr(objeto, parte)
        except (AttributeError, TypeError):
            return ""
        if callable(objeto):
            objeto = objeto()
    return "" if objeto is None else objeto


def exportar_excel(titulo, encabezados, filas, nombre_archivo):
    libro = Workbook()
    hoja = libro.active
    hoja.title = titulo[:31]
    hoja.append([titulo])
    hoja["A1"].font = Font(bold=True, size=14)
    hoja.append([])
    hoja.append(encabezados)
    for celda in hoja[3]:
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = PatternFill("solid", fgColor="A83F67")
    for fila in filas:
        hoja.append([valor if isinstance(valor, (int, float)) else str(valor or "") for valor in fila])
    for columna in hoja.columns:
        largo = max(len(str(celda.value or "")) for celda in columna)
        hoja.column_dimensions[columna[0].column_letter].width = min(largo + 2, 50)
    hoja.freeze_panes = "A4"

    buffer = BytesIO()
    libro.save(buffer)
    respuesta = HttpResponse(
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    respuesta["Content-Disposition"] = f'attachment; filename="{nombre_archivo}.xlsx"'
    return respuesta


def enlazar_archivos(uri, rel):
    """Resuelve solo archivos estáticos o multimedia dentro de sus carpetas."""
    ruta_url = unquote(urlsplit(uri).path)
    prefijos_static = {settings.STATIC_URL, f"/{settings.STATIC_URL.lstrip('/')}"}
    for prefijo in prefijos_static:
        if prefijo and ruta_url.startswith(prefijo):
            return finders.find(ruta_url[len(prefijo):].lstrip("/"))

    prefijos_media = {settings.MEDIA_URL, f"/{settings.MEDIA_URL.lstrip('/')}"}
    for prefijo in prefijos_media:
        if prefijo and ruta_url.startswith(prefijo):
            raiz = Path(settings.MEDIA_ROOT).resolve()
            destino = (raiz / ruta_url[len(prefijo):].lstrip("/")).resolve()
            if destino.is_relative_to(raiz) and destino.is_file():
                return str(destino)
    return None


def render_pdf(template, contexto, nombre_archivo, descargar=False):
    from xhtml2pdf import pisa

    html = render_to_string(template, contexto)
    buffer = BytesIO()
    resultado = pisa.CreatePDF(html, dest=buffer, link_callback=enlazar_archivos)
    if resultado.err:
        logger.error("xhtml2pdf no pudo generar %s (%s error(es))", nombre_archivo, resultado.err)
        raise RuntimeError(f"No se pudo generar el PDF {nombre_archivo}.")
    respuesta = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    modo = "attachment" if descargar else "inline"
    respuesta["Content-Disposition"] = f'{modo}; filename="{nombre_archivo}.pdf"'
    return respuesta
