"""Polygon + date-range search endpoint for Ocorrencia."""

from __future__ import annotations

import math

from django.db.models import Count
from django.db.models.functions import TruncMonth
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Ocorrencia
from .serializers import OcorrenciaSerializer, SearchRequestSerializer


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
