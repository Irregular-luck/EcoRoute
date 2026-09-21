import uuid
from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import models


class RouteSearch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_label = models.CharField(max_length=255)
    destination_label = models.CharField(max_length=255)
    source = gis_models.PointField(geography=True)
    destination = gis_models.PointField(geography=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Route(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    search = models.ForeignKey(RouteSearch, on_delete=models.CASCADE, related_name="routes")
    name = models.CharField(max_length=64)
    geometry = gis_models.LineStringField(geography=True)
    distance_km = models.DecimalField(max_digits=7, decimal_places=2)
    duration_minutes = models.PositiveIntegerField()
    road_segments = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)


class EnvironmentalReading(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name="readings")
    provider = models.CharField(max_length=32)
    aqi_average = models.PositiveIntegerField()
    aqi_maximum = models.PositiveIntegerField()
    traffic_score = models.PositiveSmallIntegerField()
    traffic_level = models.CharField(max_length=16)
    traffic_delay_minutes = models.PositiveIntegerField(default=0)
    temperature_c = models.DecimalField(max_digits=5, decimal_places=1)
    humidity_percent = models.PositiveSmallIntegerField()
    wind_speed_kph = models.DecimalField(max_digits=5, decimal_places=1)
    rain_probability = models.PositiveSmallIntegerField()
    weather_description = models.CharField(max_length=64)
    weather_impact_score = models.PositiveSmallIntegerField()
    sampled_at = models.DateTimeField(auto_now_add=True)


class NoisePrediction(models.Model):
    route = models.OneToOneField(Route, on_delete=models.CASCADE, related_name="noise_prediction")
    model_version = models.CharField(max_length=64)
    predicted_db = models.DecimalField(max_digits=5, decimal_places=1)
    input_features = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)


class SHAPExplanation(models.Model):
    prediction = models.OneToOneField(NoisePrediction, on_delete=models.CASCADE, related_name="explanation")
    contributors = models.JSONField(default=list)
    user_summary = models.TextField()


class RouteScore(models.Model):
    route = models.OneToOneField(Route, on_delete=models.CASCADE, related_name="score")
    aqi_score = models.PositiveSmallIntegerField()
    noise_score = models.PositiveSmallIntegerField()
    traffic_score = models.PositiveSmallIntegerField()
    weather_score = models.PositiveSmallIntegerField()
    environmental_risk_score = models.PositiveSmallIntegerField()
    category = models.CharField(max_length=16)
    is_recommended = models.BooleanField(default=False)


class SavedRoute(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    nickname = models.CharField(max_length=64, blank=True)
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "route"], name="unique_saved_route")]
