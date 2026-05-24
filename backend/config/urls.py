from django.contrib import admin
from django.urls import include, path

from ocorrencias.urls import (
    areas_forca_urlpatterns,
    ocorrencias_urlpatterns,
    regions_urlpatterns,
    snapshot_urlpatterns,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/ocorrencias/",  include((ocorrencias_urlpatterns, "ocorrencias"))),
    path("api/areas-forca/",  include((areas_forca_urlpatterns, "areas_forca"))),
    path("api/area-snapshot/", include((snapshot_urlpatterns, "area_snapshot"))),
    path("api/regions/",      include((regions_urlpatterns, "regions"))),
]
