"""Polygon + date-range search endpoint for Ocorrencia."""

from __future__ import annotations

import math

from django.db.models import Count
from django.db.models.functions import TruncMonth
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AreaForca, Camera, DiskDenuncia, FatorUrbano, Ocorrencia
from .regions_logic import compute_region_list
from .scoring import CRIME_WEIGHTS, compute_scores
from .serializers import (
    AreaForcaFeatureSerializer,
    AreaForcaScoreQuerySerializer,
    AreaForcaScoreSerializer,
    AreaSnapshotRequestSerializer,
    CameraSerializer,
    DiskDenunciaSerializer,
    FatorUrbanoSerializer,
    OcorrenciaSerializer,
    RegionListQuerySerializer,
    RegionSerializer,
    SearchRequestSerializer,
)

# Safety cap per dataset so a huge area can't return unbounded rows.
MAX_ROWS_PER_DATASET = 5000


class OcorrenciaSearchView(APIView):
    """POST /api/ocorrencias/search/

    Body:
        {
          "polygon": [[lat, lng], ...],   # closed ring optional
          "start_date": "YYYY-MM-DD",
          "end_date":   "YYYY-MM-DD",
          "page": 1,
          "page_size": 500
        }

    Response: {summary, pagination, results}
    """

    def post(self, request):
        req = SearchRequestSerializer(data=request.data)
        req.is_valid(raise_exception=True)
        poly = req.build_geometry()
        v = req.validated_data
        page = v["page"]
        page_size = v["page_size"]

        qs = Ocorrencia.objects.filter(
            location__within=poly,
            data__gte=v["start_date"],
            data__lte=v["end_date"],
        )

        total = qs.count()

        by_desc = list(
            qs.values("desc_delito")
            .annotate(count=Count("pk"))
            .order_by("-count", "desc_delito")
        )
        by_month = [
            {"month": row["m"].strftime("%Y-%m"), "count": row["count"]}
            for row in qs.annotate(m=TruncMonth("data"))
            .values("m")
            .annotate(count=Count("pk"))
            .order_by("m")
        ]
        by_aisp = list(
            qs.exclude(aisp__isnull=True)
            .values("aisp")
            .annotate(count=Count("pk"))
            .order_by("-count")
        )

        offset = (page - 1) * page_size
        page_qs = qs.order_by("-data", "id_criptografado")[offset : offset + page_size]
        results = OcorrenciaSerializer(page_qs, many=True).data
        total_pages = math.ceil(total / page_size) if total else 0

        return Response(
            {
                "summary": {
                    "total": total,
                    "by_desc_delito": by_desc,
                    "by_month": by_month,
                    "by_aisp": by_aisp,
                },
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "total_pages": total_pages,
                },
                "results": results,
            },
            status=status.HTTP_200_OK,
        )


class AreaForcaScoreListView(APIView):
    """GET /api/areas-forca/scores/?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD

    Returns a risk score (0-100) for each Área de Força polygon based on the
    weighted density of Ocorrencias inside it during the optional date window.
    """

    def get(self, request):
        q = AreaForcaScoreQuerySerializer(data=request.query_params)
        q.is_valid(raise_exception=True)
        v = q.validated_data
        scored = compute_scores(start_date=v["start_date"], end_date=v["end_date"])
        return Response(
            {
                "date_range": {
                    "start_date": v["start_date"].isoformat(),
                    "end_date":   v["end_date"].isoformat(),
                },
                "weights": CRIME_WEIGHTS,
                "results": AreaForcaScoreSerializer(scored, many=True).data,
            },
            status=status.HTTP_200_OK,
        )


class AreasForcaListView(APIView):
    """GET /api/areas-forca/ -> GeoJSON FeatureCollection of all áreas de força.

    Matches the shape the frontend's AreasLayer.tsx already consumes from the
    static `/data/areas-forca.geojson` file.
    """

    def get(self, request):
        qs = AreaForca.objects.all().order_by("fid")
        return Response(AreaForcaFeatureSerializer(qs, many=True).data)


class RegionListView(APIView):
    """GET /api/regions/?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD

    Returns one entry per ``AreaForca`` polygon with the headline score,
    operational counts (roubos/denuncias/ambiente), and the 5 criteria
    that back the score bar in the frontend ``RegionList`` panel.
    """

    def get(self, request):
        q = RegionListQuerySerializer(data=request.query_params)
        q.is_valid(raise_exception=True)
        v = q.validated_data
        results = compute_region_list(v["start_date"], v["end_date"])
        return Response(
            {
                "date_range": {
                    "start_date": v["start_date"].isoformat(),
                    "end_date":   v["end_date"].isoformat(),
                },
                "results": RegionSerializer(results, many=True).data,
            },
            status=status.HTTP_200_OK,
        )


class AreaSnapshotView(APIView):
    """POST /api/area-snapshot/

    Body:
        {
          "fid": <int>,              # primary key of an area_forca row
          "start_date": "YYYY-MM-DD",
          "end_date":   "YYYY-MM-DD"
        }

    Looks up the area_forca geometry by fid and returns all rows from each
    dataset that fall within it. Datasets without a date column (cameras,
    fatores_urbanos) ignore the date range and are filtered by geometry only.
    """

    def post(self, request):
        req = AreaSnapshotRequestSerializer(data=request.data)
        req.is_valid(raise_exception=True)
        v = req.validated_data
        try:
            area = AreaForca.objects.get(fid=v["fid"])
        except AreaForca.DoesNotExist:
            raise NotFound(f"area_forca with fid={v['fid']} not found")

        geom = area.geometry
        start, end = v["start_date"], v["end_date"]

        return Response(
            {
                "area_forca": {
                    "fid": area.fid,
                    "nome_subar": area.nome_subar,
                    "area_km2": area.area_km2,
                },
                "ocorrencias": self._ocorrencias(geom, start, end),
                "denuncias": self._denuncias(geom, start, end),
                "cameras": self._cameras(geom),
                "fatores_urbanos": self._fatores_urbanos(geom),
            }
        )

    def _ocorrencias(self, geom, start, end) -> dict:
        qs = Ocorrencia.objects.filter(
            location__within=geom,
            data__gte=start,
            data__lte=end,
        )
        total = qs.count()
        by_desc = list(
            qs.values("desc_delito")
            .annotate(count=Count("pk"))
            .order_by("-count", "desc_delito")
        )
        page_qs = qs.order_by("-data", "id_criptografado")[:MAX_ROWS_PER_DATASET]
        return {
            "summary": {
                "total": total,
                "truncated": total > MAX_ROWS_PER_DATASET,
                "by_desc_delito": by_desc,
            },
            "results": OcorrenciaSerializer(page_qs, many=True).data,
        }

    def _denuncias(self, geom, start, end) -> dict:
        # data_denuncia is a DateTimeField; use __date for inclusive day-range matching.
        qs = DiskDenuncia.objects.filter(
            location__within=geom,
            data_denuncia__date__gte=start,
            data_denuncia__date__lte=end,
        )
        total = qs.count()
        by_classe = list(
            qs.exclude(classe="")
            .values("classe")
            .annotate(count=Count("pk"))
            .order_by("-count", "classe")
        )
        page_qs = qs.order_by("-data_denuncia", "pk")[:MAX_ROWS_PER_DATASET]
        return {
            "summary": {
                "total": total,
                "truncated": total > MAX_ROWS_PER_DATASET,
                "by_classe": by_classe,
            },
            "results": DiskDenunciaSerializer(page_qs, many=True).data,
        }

    def _cameras(self, geom) -> dict:
        qs = Camera.objects.filter(location__within=geom)
        total = qs.count()
        page_qs = qs.order_by("id_ponto")[:MAX_ROWS_PER_DATASET]
        return {
            "summary": {
                "total": total,
                "truncated": total > MAX_ROWS_PER_DATASET,
            },
            "results": CameraSerializer(page_qs, many=True).data,
        }

    def _fatores_urbanos(self, geom) -> dict:
        qs = FatorUrbano.objects.filter(location__within=geom)
        total = qs.count()
        by_tipo = list(
            qs.exclude(tipo_ocorrencia_descricao="")
            .values("tipo_ocorrencia_descricao")
            .annotate(count=Count("pk"))
            .order_by("-count", "tipo_ocorrencia_descricao")
        )
        page_qs = qs.order_by("pk")[:MAX_ROWS_PER_DATASET]
        return {
            "summary": {
                "total": total,
                "truncated": total > MAX_ROWS_PER_DATASET,
                "by_tipo_ocorrencia": by_tipo,
            },
            "results": FatorUrbanoSerializer(page_qs, many=True).data,
        }
