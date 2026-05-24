from django.urls import path

from .views import (
    AreaForcaScoreListView,
    AreasForcaListView,
    AreaSnapshotView,
    OcorrenciaSearchView,
)

ocorrencias_urlpatterns = [
    path("search/", OcorrenciaSearchView.as_view(), name="ocorrencia-search"),
]

areas_forca_urlpatterns = [
    path("", AreasForcaListView.as_view(), name="areaforca-list"),
    path("scores/", AreaForcaScoreListView.as_view(), name="areaforca-scores"),
]

snapshot_urlpatterns = [
    path("", AreaSnapshotView.as_view(), name="area-snapshot"),
]

# Default export: kept for backward compat with the original include().
urlpatterns = ocorrencias_urlpatterns
