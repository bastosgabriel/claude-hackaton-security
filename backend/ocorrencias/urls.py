from django.urls import path

from .views import OcorrenciaSearchView

urlpatterns = [
    path("search/", OcorrenciaSearchView.as_view(), name="ocorrencia-search"),
]
