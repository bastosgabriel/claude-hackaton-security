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
