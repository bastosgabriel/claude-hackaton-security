from django.urls import path

from .views import AreaForcaScoreListView, OcorrenciaSearchView

ocorrencias_urlpatterns = [
    path("search/", OcorrenciaSearchView.as_view(), name="ocorrencia-search"),
]

areas_forca_urlpatterns = [
    path("scores/", AreaForcaScoreListView.as_view(), name="areaforca-scores"),
]

# Default export: kept for backward compat with the original include().
urlpatterns = ocorrencias_urlpatterns
