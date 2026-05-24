from django.contrib.gis import admin

from .models import Ocorrencia


@admin.register(Ocorrencia)
class OcorrenciaAdmin(admin.GISModelAdmin):
    list_display = ("id_criptografado", "data", "desc_delito", "aisp", "risp", "locf")
    list_filter = ("desc_delito", "ano", "mes", "aisp", "risp")
    search_fields = ("id_criptografado", "locf")
    readonly_fields = ("id_criptografado",)
