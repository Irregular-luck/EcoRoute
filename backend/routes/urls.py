from django.urls import path
from .views import AnalyticsView, LatestEnvironmentalView, NoisePredictionView, RiskCalculationView, RouteRecommendationView

urlpatterns = [
    path("routes", RouteRecommendationView.as_view(), name="routes"),
    path("predict-noise", NoisePredictionView.as_view(), name="predict-noise"),
    path("calculate-risk", RiskCalculationView.as_view(), name="calculate-risk"),
    path("aqi", LatestEnvironmentalView.as_view(), name="aqi"),
    path("traffic", LatestEnvironmentalView.as_view(), name="traffic"),
    path("weather", LatestEnvironmentalView.as_view(), name="weather"),
    path("recommendation", LatestEnvironmentalView.as_view(), name="recommendation"),
    path("analytics", AnalyticsView.as_view(), name="analytics"),
]
