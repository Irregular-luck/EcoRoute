from dataclasses import asdict
from django.db.models import Avg
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import AnonRateThrottle

from .models import EnvironmentalReading, RouteScore
from .noise import NoisePredictor
from .risk import calculate_risk
from .serializers import NoiseRequestSerializer, RiskRequestSerializer, RouteRequestSerializer
from .services import LocationNotFoundError, build_recommendations, persist_recommendations


class RouteRecommendationView(APIView):
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        serializer = RouteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = build_recommendations(
                source_label=serializer.validated_data["source"],
                destination_label=serializer.validated_data["destination"],
            )
        except LocationNotFoundError as error:
            return Response({"detail": str(error)}, status=400)
        routes = persist_recommendations(result)
        return Response({"source": result["source"], "destination": result["destination"], "routes": routes})


class NoisePredictionView(APIView):
    def post(self, request):
        serializer = NoiseRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        prediction = NoisePredictor().predict(**serializer.validated_data)
        return Response({"predicted_db": prediction.decibels, "model_version": prediction.model_version, "contributors": prediction.contributors, "explanation": prediction.summary})


class RiskCalculationView(APIView):
    def post(self, request):
        serializer = RiskRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(asdict(calculate_risk(**serializer.validated_data)))


class LatestEnvironmentalView(APIView):
    field = "aqi_average"

    def get(self, request):
        reading = EnvironmentalReading.objects.order_by("-sampled_at").first()
        if not reading:
            return Response({"detail": "No route analysis has been run yet."}, status=404)
        payload = {"aqi": reading.aqi_average, "traffic": reading.traffic_score, "weather": reading.weather_description, "provider": reading.provider, "sampled_at": reading.sampled_at}
        return Response(payload)


class AnalyticsView(APIView):
    def get(self, request):
        risk = RouteScore.objects.aggregate(average=Avg("environmental_risk_score"))["average"]
        return Response({"analysed_routes": RouteScore.objects.count(), "average_environmental_risk": round(risk or 0, 1), "note": "Use this endpoint as the data source for exposure trend charts."})
