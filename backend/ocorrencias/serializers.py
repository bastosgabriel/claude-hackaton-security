"""DRF serializers for the polygon-date search endpoint."""

from __future__ import annotations

import datetime as dt
import json

from django.contrib.gis.geos import GEOSGeometry, Polygon
from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from .models import AreaForca

DATE_MIN = dt.date(2000, 1, 1)
MAX_PAGE_SIZE = 2000
DEFAULT_PAGE_SIZE = 500


class SearchRequestSerializer(serializers.Serializer):
    """Validates a polygon-date search request.

    Frontend convention: polygon is a list of [lat, lng] pairs (ring). We swap
    them to (lng, lat) before building the PostGIS Polygon.
    """

    polygon = serializers.ListField(
        child=serializers.ListField(
            child=serializers.FloatField(),
            min_length=2,
            max_length=2,
        ),
        min_length=3,
    )
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    page = serializers.IntegerField(default=1, min_value=1)
    page_size = serializers.IntegerField(
        default=DEFAULT_PAGE_SIZE, min_value=1, max_value=MAX_PAGE_SIZE
    )

    def validate(self, attrs):
        if attrs["start_date"] > attrs["end_date"]:
            raise serializers.ValidationError("start_date must be <= end_date")
        today = dt.date.today()
        if attrs["start_date"] < DATE_MIN or attrs["end_date"] > today:
            raise serializers.ValidationError(
                f"dates must lie within [{DATE_MIN.isoformat()}, {today.isoformat()}]"
            )
        return attrs

    def validate_polygon(self, value):
        for pt in value:
            lat, lng = pt
            if not (-90 <= lat <= 90):
                raise serializers.ValidationError(f"latitude out of range: {lat}")
            if not (-180 <= lng <= 180):
                raise serializers.ValidationError(f"longitude out of range: {lng}")
        return value

    def build_geometry(self) -> Polygon:
        pts = list(self.validated_data["polygon"])
        # [lat, lng] -> (lng, lat) and close ring if needed
        ring = [(lng, lat) for lat, lng in pts]
        if ring[0] != ring[-1]:
            ring.append(ring[0])
        if len(ring) < 4:
            raise serializers.ValidationError("polygon needs at least 3 distinct points")
        poly = Polygon(ring, srid=4326)
        if not poly.valid:
            raise serializers.ValidationError(f"invalid polygon: {poly.valid_reason}")
        return poly


class OcorrenciaSerializer(serializers.Serializer):
    """Output shape for a single occurrence row."""

    id = serializers.CharField(source="id_criptografado")
    lat = serializers.SerializerMethodField()
    lng = serializers.SerializerMethodField()
    data = serializers.DateField()
    desc_delito = serializers.CharField()
    aisp = serializers.IntegerField(allow_null=True)
    risp = serializers.IntegerField(allow_null=True)
    locf = serializers.CharField(allow_blank=True)

    def get_lat(self, obj) -> float:
        return obj.location.y

    def get_lng(self, obj) -> float:
        return obj.location.x


class AreaForcaScoreSerializer(serializers.Serializer):
    """Output shape for one polygon's risk score.

    ``score`` is the combined risk factor (0-100, weighted average of the three
    component scores). ``ocorrencia_score``, ``denuncia_score`` and
    ``camera_score`` expose the components for inspection / charting.
    """

    fid = serializers.IntegerField()
    nome_subar = serializers.CharField()
    area_km2 = serializers.FloatField()
    geometry = serializers.SerializerMethodField()
    occurrence_count = serializers.IntegerField()
    weighted_count = serializers.FloatField()
    density = serializers.FloatField()
    ocorrencia_score = serializers.FloatField()
    denuncia_count = serializers.IntegerField()
    denuncia_density = serializers.FloatField()
    denuncia_score = serializers.FloatField()
    camera_count = serializers.IntegerField()
    camera_density = serializers.FloatField()
    camera_score = serializers.FloatField()
    score = serializers.FloatField()
    score_raw = serializers.FloatField()
    by_desc_delito = serializers.ListField(child=serializers.DictField())
    by_year = serializers.ListField(child=serializers.DictField())

    def get_geometry(self, obj) -> dict:
        return json.loads(obj["geometry"].geojson)


class AreaForcaScoreQuerySerializer(serializers.Serializer):
    """Validates the optional date window for the score endpoint."""

    start_date = serializers.DateField(required=False, default=DATE_MIN)
    end_date = serializers.DateField(required=False)

    def validate(self, attrs):
        today = dt.date.today()
        end = attrs.get("end_date") or today
        attrs["end_date"] = end
        if attrs["start_date"] > end:
            raise serializers.ValidationError("start_date must be <= end_date")
        if attrs["start_date"] < DATE_MIN or end > today:
            raise serializers.ValidationError(
                f"dates must lie within [{DATE_MIN.isoformat()}, {today.isoformat()}]"
            )
        return attrs


class RegionListQuerySerializer(serializers.Serializer):
    """Validates the date window for ``GET /api/regions/``."""

    start_date = serializers.DateField()
    end_date = serializers.DateField()

    def validate(self, attrs):
        if attrs["start_date"] > attrs["end_date"]:
            raise serializers.ValidationError("start_date must be <= end_date")
        today = dt.date.today()
        if attrs["start_date"] < DATE_MIN or attrs["end_date"] > today:
            raise serializers.ValidationError(
                f"dates must lie within [{DATE_MIN.isoformat()}, {today.isoformat()}]"
            )
        return attrs


class RegionCriterionSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    value = serializers.CharField()
    pct = serializers.IntegerField()
    level = serializers.CharField()


class RegionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    aisp = serializers.CharField(allow_blank=True)
    score = serializers.IntegerField()
    level = serializers.CharField()
    roubos = serializers.IntegerField()
    denuncias = serializers.IntegerField()
    ambiente = serializers.IntegerField()
    criteria = RegionCriterionSerializer(many=True)
    narrative = serializers.CharField(allow_blank=True)
    actions = serializers.ListField(child=serializers.DictField())


class AreaSnapshotRequestSerializer(serializers.Serializer):
    """Validates a snapshot request: { fid, start_date, end_date }."""

    fid = serializers.IntegerField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()

    def validate(self, attrs):
        if attrs["start_date"] > attrs["end_date"]:
            raise serializers.ValidationError("start_date must be <= end_date")
        today = dt.date.today()
        if attrs["start_date"] < DATE_MIN or attrs["end_date"] > today:
            raise serializers.ValidationError(
                f"dates must lie within [{DATE_MIN.isoformat()}, {today.isoformat()}]"
            )
        return attrs


class AreaForcaFeatureSerializer(GeoFeatureModelSerializer):
    """GeoJSON Feature representation of an AreaForca row.

    Properties carry `fid` and `nome_subar` so the existing AreasLayer.tsx
    on the frontend can consume the response unchanged.
    """

    class Meta:
        model = AreaForca
        geo_field = "geometry"
        id_field = False
        fields = ("fid", "nome_subar", "area_km2")


class _PointMixin:
    def get_lat(self, obj) -> float:
        return obj.location.y if obj.location else None

    def get_lng(self, obj) -> float:
        return obj.location.x if obj.location else None


class CameraSerializer(_PointMixin, serializers.Serializer):
    id = serializers.CharField(source="id_ponto")
    lat = serializers.SerializerMethodField()
    lng = serializers.SerializerMethodField()
    nome_area_fm = serializers.CharField(allow_blank=True)
    id_trecho = serializers.IntegerField()


class FatorUrbanoSerializer(_PointMixin, serializers.Serializer):
    id = serializers.IntegerField(source="id_resposta_ocorrencia")
    lat = serializers.SerializerMethodField()
    lng = serializers.SerializerMethodField()
    logradouro = serializers.CharField(allow_blank=True)
    numero_porta = serializers.CharField(allow_blank=True)
    bairro_nome = serializers.CharField(allow_blank=True)
    subarea_nome = serializers.CharField(allow_blank=True)
    tipo_ocorrencia_descricao = serializers.CharField(allow_blank=True)
    orgao_responsavel = serializers.CharField(allow_blank=True)


class DiskDenunciaSerializer(_PointMixin, serializers.Serializer):
    id = serializers.IntegerField(source="id_denuncia")
    lat = serializers.SerializerMethodField()
    lng = serializers.SerializerMethodField()
    numero_denuncia = serializers.CharField(allow_blank=True)
    data_denuncia = serializers.DateTimeField(allow_null=True)
    data_difusao = serializers.DateTimeField(allow_null=True)
    bairro_logradouro = serializers.CharField(allow_blank=True)
    subbairro_logradouro = serializers.CharField(allow_blank=True)
    municipio = serializers.CharField(allow_blank=True)
    estado = serializers.CharField(allow_blank=True)
    orgao_nome = serializers.CharField(allow_blank=True)
    orgao_tipo = serializers.CharField(allow_blank=True)
    classe = serializers.CharField(allow_blank=True)
    tipo = serializers.CharField(allow_blank=True)
    status_denuncia = serializers.CharField(allow_blank=True)
    relato_redacted = serializers.CharField(allow_blank=True)
