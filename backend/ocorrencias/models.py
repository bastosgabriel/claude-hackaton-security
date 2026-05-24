from django.contrib.gis.db import models as gismodels
from django.db import models


class Ocorrencia(models.Model):
    id_criptografado = models.CharField(primary_key=True, max_length=64)
    ano = models.SmallIntegerField()
    mes = models.SmallIntegerField()
    data = models.DateField(null=True, blank=True, db_index=True)
    hora = models.TimeField(null=True, blank=True)
    delito = models.IntegerField(null=True, blank=True)
    desc_delito = models.CharField(max_length=120, db_index=True)
    aisp = models.SmallIntegerField(null=True, blank=True, db_index=True)
    risp = models.SmallIntegerField(null=True, blank=True, db_index=True)
    locf = models.CharField(max_length=255, blank=True)
    dia_semana = models.CharField(max_length=20, blank=True)
    location = gismodels.PointField(srid=4326, spatial_index=True)

    class Meta:
        indexes = [models.Index(fields=["data", "desc_delito"])]

    def __str__(self) -> str:
        return f"{self.desc_delito} @ {self.data} ({self.id_criptografado[:8]})"


class Camera(models.Model):
    """Surveillance cameras from `cameras_areas_fm.csv` (985 rows)."""

    id_ponto = models.CharField(primary_key=True, max_length=36)  # UUID v4
    nome_area_fm = models.CharField(max_length=120, db_index=True)
    id_trecho = models.PositiveIntegerField(db_index=True)
    location = gismodels.PointField(srid=4326, spatial_index=True)

    class Meta:
        indexes = [models.Index(fields=["nome_area_fm", "id_trecho"])]

    def __str__(self) -> str:
        return f"Camera {self.id_ponto[:8]} ({self.nome_area_fm})"


class DiskDenuncia(models.Model):
    """Anonymous-tip-line complaints from `disk_denuncia.csv`.

    Stores only **parent** rows (one per complaint). The CSV is denormalized
    with one parent + N child rows for orgs/subjects/persons; child rows are
    discarded in this flat model (~18k parent rows out of ~83k physical rows).
    """

    id_denuncia = models.IntegerField(primary_key=True)
    numero_denuncia = models.CharField(max_length=30, unique=True, db_index=True)

    # Dates (CSV format: M/D/YYYY H:MM:SS — US month-first)
    data_denuncia = models.DateTimeField(null=True, blank=True, db_index=True)
    data_difusao = models.DateTimeField(null=True, blank=True)
    timestamp_insercao = models.DateTimeField(null=True, blank=True)

    # Address
    tipo_logradouro = models.CharField(max_length=10, blank=True)
    logradouro = models.CharField(max_length=120, blank=True)
    numero_logradouro = models.CharField(max_length=20, blank=True)
    complemento_logradouro = models.CharField(max_length=120, blank=True)
    bairro_logradouro = models.CharField(max_length=80, blank=True, db_index=True)
    subbairro_logradouro = models.CharField(max_length=80, blank=True)
    cep_logradouro = models.CharField(max_length=9, blank=True)
    referencia_logradouro = models.CharField(max_length=255, blank=True)
    municipio = models.CharField(max_length=80, blank=True)
    estado = models.CharField(max_length=2, blank=True)

    # Geolocation (~3% of parent rows have no coords)
    location = gismodels.PointField(srid=4326, spatial_index=True, null=True, blank=True)

    # Special alert tag
    xpto_id = models.IntegerField(null=True, blank=True)
    xpto_nome = models.CharField(max_length=80, blank=True)

    # Primary receiving agency
    orgao_id = models.IntegerField(null=True, blank=True)
    orgao_nome = models.CharField(max_length=100, blank=True)
    orgao_tipo = models.CharField(max_length=12, blank=True)  # OPERACIONAL | INFORMATIVA

    # Primary crime subject
    id_classe = models.SmallIntegerField(null=True, blank=True, db_index=True)
    classe = models.CharField(max_length=100, blank=True, db_index=True)
    id_tipo = models.SmallIntegerField(null=True, blank=True, db_index=True)
    tipo = models.CharField(max_length=100, blank=True)
    assunto_principal = models.BooleanField(null=True, blank=True)

    # Involved person (first/only)
    envolvido_id = models.IntegerField(null=True, blank=True)
    envolvido_sexo = models.CharField(max_length=1, blank=True)
    envolvido_idade = models.SmallIntegerField(null=True, blank=True)
    envolvido_pele = models.CharField(max_length=20, blank=True)
    envolvido_estatura = models.CharField(max_length=10, blank=True)
    envolvido_porte = models.CharField(max_length=10, blank=True)
    envolvido_cabelos = models.CharField(max_length=40, blank=True)
    envolvido_olhos = models.CharField(max_length=40, blank=True)
    envolvido_outras_caracteristicas = models.TextField(blank=True)

    status_denuncia = models.CharField(max_length=40, blank=True, db_index=True)
    relato_redacted = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["data_denuncia", "classe"]),
            models.Index(fields=["bairro_logradouro", "classe"]),
        ]

    def __str__(self) -> str:
        return f"{self.numero_denuncia} — {self.tipo} ({self.bairro_logradouro})"


class AreaForca(models.Model):
    """Municipal "área de força" polygons from `sh_area_forca/areas_forca_municipal.shp`.

    Each row is one priority public-safety zone. `area_km2` is precomputed by
    the loader (reprojected to SIRGAS 2000 / UTM 23S, EPSG:31983) so the
    scorer doesn't have to reproject at query time.
    """

    fid = models.IntegerField(primary_key=True)
    nome_subar = models.CharField(max_length=255, db_index=True)
    area_km2 = models.FloatField()
    geometry = gismodels.PolygonField(srid=4326, spatial_index=True)

    def __str__(self) -> str:
        return f"[fid {self.fid}] {self.nome_subar}"


class FatorUrbano(models.Model):
    """Urban-factor survey responses from `fatores_urbanos.csv`.

    Each record represents a single street-level urban condition (poor
    lighting, vegetation blocking visibility, drug-use scenes, homeless
    occupation, etc.) classified by `tipo_ocorrencia_descricao`.

    NOTE: in the CSV, `coordenada_x` is **latitude** and `coordenada_y` is
    **longitude** — inverted from typical GIS convention. The ETL handles
    this by passing `(coordenada_y, coordenada_x)` to `Point(lng, lat)`.
    """

    id_resposta_ocorrencia = models.IntegerField(primary_key=True)

    logradouro = models.CharField(max_length=255, blank=True)
    numero_porta = models.CharField(max_length=64, blank=True)
    referencia = models.CharField(max_length=512, blank=True)
    observacao = models.TextField(blank=True)
    location = gismodels.PointField(srid=4326, spatial_index=True)

    endereco_informado = models.BooleanField(null=True, blank=True)
    valido = models.BooleanField(null=True, blank=True)
    id_bairro = models.IntegerField(null=True, blank=True)
    bairro_nome = models.CharField(max_length=120, blank=True)
    id_subarea = models.IntegerField(null=True, blank=True)
    subarea_nome = models.CharField(max_length=255, blank=True)

    # Main category (always present)
    id_tipo_ocorrencia = models.SmallIntegerField(db_index=True)
    tipo_ocorrencia_descricao = models.CharField(max_length=255, db_index=True)
    tipo_ocorrencia_ativo = models.BooleanField(null=True, blank=True)

    # Responsible agency
    orgao_responsavel = models.CharField(max_length=64, blank=True)
    id_orgao_ocorrencia = models.SmallIntegerField(null=True, blank=True)
    ocorrencia_orgao_nome = models.CharField(max_length=64, blank=True)
    codigo_ocorrencia_orgao = models.IntegerField(null=True, blank=True)

    # Conditional — "Pessoas em situação de rua" (tipo 19)
    id_tipo_pessoa = models.SmallIntegerField(null=True, blank=True)
    tipo_pessoa_descricao = models.CharField(max_length=120, blank=True)
    id_ocupacao_pessoa = models.SmallIntegerField(null=True, blank=True)
    ocupacao_pessoa_descricao = models.CharField(max_length=120, blank=True)
    id_tipo_frequencia = models.SmallIntegerField(null=True, blank=True)
    tipo_frequencia_descricao = models.CharField(max_length=120, blank=True)

    # Conditional — drug scenes
    ocupacao_drogas = models.SmallIntegerField(null=True, blank=True)
    ocupacao_drogas_descricao = models.CharField(max_length=120, blank=True)

    # Conditional — squares/parks (tipo 21)
    id_item_praca = models.SmallIntegerField(null=True, blank=True)
    item_praca_descricao = models.CharField(max_length=255, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["id_tipo_ocorrencia", "bairro_nome"]),
            models.Index(fields=["id_subarea"]),
        ]

    def __str__(self) -> str:
        return f"{self.tipo_ocorrencia_descricao} @ {self.logradouro}"
