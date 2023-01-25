from django.db import models
from django.utils import timezone


class Place(models.Model):
    address = models.CharField(
        'Адрес',
        max_length=50
    )
    lat = models.FloatField(
        'Широта',
        blank=True,
        null=True
    )
    lon = models.FloatField(
        'Долгота',
        blank=True,
        null=True
    )
    updated = models.DateTimeField(
        default=timezone.now(),
        db_index=True,
    )

    class Meta:
        verbose_name='Место',
        verbose_name_plural='Места'

    def __str__(self):
        return self.address
