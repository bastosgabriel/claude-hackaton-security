"""DRF serializers for the polygon-date search endpoint."""

from __future__ import annotations

import datetime as dt
import json

from django.contrib.gis.geos import GEOSGeometry, Polygon
from rest_framework import serializers

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
    """Output shape for one polygon's risk score."""

    fid = serializers.IntegerField()
    nome_subar = serializers.CharField()
    area_km2 = serializers.FloatField()
    geometry = serializers.SerializerMethodField()
    occurrence_count = serializers.IntegerField()
    weighted_count = serializers.FloatField()
    density = serializers.FloatField()
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
