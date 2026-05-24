from django.contrib.gis import admin

from .models import Camera, DiskDenuncia, FatorUrbano, Ocorrencia


@admin.register(Ocorrencia)
class OcorrenciaAdmin(admin.GISModelAdmin):
    list_display = ("id_criptografado", "data", "desc_delito", "aisp", "risp", "locf")
    list_filter = ("desc_delito", "ano", "mes", "aisp", "risp")
    search_fields = ("id_criptografado", "locf")
    readonly_fields = ("id_criptografado",)


@admin.register(Camera)
class CameraAdmin(admin.GISModelAdmin):
    list_display = ("id_ponto", "nome_area_fm", "id_trecho")
    list_filter = ("nome_area_fm",)
    search_fields = ("id_ponto", "id_trecho")
    readonly_fields = ("id_ponto",)


@admin.register(DiskDenuncia)
class DiskDenunciaAdmin(admin.GISModelAdmin):
    list_display = (
        "numero_denuncia", "data_denuncia", "classe", "tipo",
        "bairro_logradouro", "status_denuncia",
    )
    list_filter = ("classe", "status_denuncia", "orgao_tipo", "bairro_logradouro")
    search_fields = ("numero_denuncia", "logradouro", "bairro_logradouro")
    readonly_fields = ("id_denuncia", "numero_denuncia")


@admin.register(FatorUrbano)
class FatorUrbanoAdmin(admin.GISModelAdmin):
    list_display = (
        "id_resposta_ocorrencia", "tipo_ocorrencia_descricao",
        "logradouro", "bairro_nome", "orgao_responsavel",
    )
    list_filter = ("tipo_ocorrencia_descricao", "orgao_responsavel", "bairro_nome")
    search_fields = ("logradouro", "bairro_nome", "referencia")
    readonly_fields = ("id_resposta_ocorrencia",)
