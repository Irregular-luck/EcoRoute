from dataclasses import asdict, dataclass
from functools import lru_cache
import hashlib
import random
import re
from typing import Any

import requests
from django.conf import settings
from django.contrib.gis.geos import LineString, Point
from django.db import transaction

from .models import EnvironmentalReading, NoisePrediction, Route, RouteScore, RouteSearch, SHAPExplanation
from .noise import NoisePredictor
from .risk import calculate_risk

KNOWN_LOCATIONS = {
    "bengaluru": (77.5946, 12.9716), "bangalore": (77.5946, 12.9716),
    "indiranagar": (77.6408, 12.9784), "koramangala": (77.6245, 12.9352),
    "delhi": (77.1025, 28.7041), "mumbai": (72.8777, 19.0760),
    "chennai": (80.2707, 13.0827), "hyderabad": (78.4867, 17.3850),
}


@dataclass(frozen=True)
class Candidate:
    name: str
    coordinates: list[list[float]]
    distance_km: float
    duration_minutes: int
    road_segments: list[str]


class LocationNotFoundError(ValueError):
    pass


@lru_cache(maxsize=512)
def geocode_location(label: str) -> tuple[float, float] | None:
    try:
        response = requests.get(
            f"{settings.GEOCODER_BASE_URL.rstrip('/')}/search",
            params={"q": label, "format": "jsonv2", "limit": 1},
            headers={"User-Agent": settings.GEOCODER_USER_AGENT},
            timeout=7,
        )
        response.raise_for_status()
        results = response.json()
        if not results:
            return None
        lat = float(results[0]["lat"])
        lon = float(results[0]["lon"])
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return lon, lat
    except (requests.RequestException, KeyError, TypeError, ValueError):
        return None
    return None


def resolve_location(label: str) -> tuple[float, float]:
    normalized = label.casefold().strip()
    if normalized in KNOWN_LOCATIONS:
        return KNOWN_LOCATIONS[normalized]
    match = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*", label)
    if match:
        lat, lon = map(float, match.groups())
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return lon, lat
    location = geocode_location(label.strip())
    if location:
        return location
    raise LocationNotFoundError(f"Could not find the location: {label}.")


def fallback_routes(origin: tuple[float, float], destination: tuple[float, float]) -> list[Candidate]:
    ox, oy = origin
    dx, dy = destination
    distance = max(2.0, ((dx - ox) ** 2 + (dy - oy) ** 2) ** .5 * 102)
    variants = [("Route A", .0, .0, 1.0), ("Route B", .012, -.008, 1.12), ("Route C", -.010, .011, .93)]
    return [Candidate(name, [[ox, oy], [(ox + dx) / 2 + bx, (oy + dy) / 2 + by], [dx, dy]], round(distance * factor, 1), round(distance * factor * 2.2), ["primary", "secondary", "residential"]) for name, bx, by, factor in variants]


def generate_routes(origin: tuple[float, float], destination: tuple[float, float]) -> list[Candidate]:
    """Use OSRM alternatives when reachable; preserve a reliable offline development path."""
    try:
        url = f"{settings.OSRM_BASE_URL.rstrip('/')}/route/v1/driving/{origin[0]},{origin[1]};{destination[0]},{destination[1]}"
        response = requests.get(url, params={"alternatives": "true", "overview": "full", "geometries": "geojson", "steps": "true"}, timeout=7)
        response.raise_for_status()
        payload = response.json()
        routes = payload.get("routes", [])[:3]
        if len(routes) >= 3:
            candidates = []
            for index, item in enumerate(routes):
                legs = item.get("legs", [])
                segments = [step.get("name") or step.get("ref") or "road" for leg in legs for step in leg.get("steps", [])]
                candidates.append(Candidate(f"Route {chr(65 + index)}", item["geometry"]["coordinates"], round(item["distance"] / 1000, 1), max(1, round(item["duration"] / 60)), segments[:50]))
            return candidates
    except (requests.RequestException, ValueError, KeyError):
        pass
    return fallback_routes(origin, destination)


def demo_metrics(candidate: Candidate, index: int) -> dict[str, Any]:
    seed = int(hashlib.sha256((candidate.name + str(candidate.distance_km)).encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    traffic = min(96, 30 + index * 17 + rng.randint(0, 15))
    aqi = min(220, 45 + index * 21 + rng.randint(0, 18))
    rain = rng.randint(5, 55)
    return {
        "source": "demo", "aqi_average": aqi, "aqi_maximum": aqi + rng.randint(5, 25),
        "traffic_score": traffic, "traffic_level": "Low" if traffic < 35 else "Moderate" if traffic < 60 else "Heavy" if traffic < 80 else "Severe",
        "traffic_delay_minutes": round(candidate.duration_minutes * traffic / 230),
        "temperature_c": round(23 + rng.random() * 10, 1), "humidity_percent": rng.randint(45, 82),
        "wind_speed_kph": round(5 + rng.random() * 18, 1), "rain_probability": rain,
        "weather_description": "light rain" if rain > 45 else "partly cloudy" if rain > 20 else "clear",
        "weather_impact_score": min(100, round(rain * .8 + rng.randint(0, 10))),
        "motorcycle_share": rng.randint(18, 42), "bus_share": rng.randint(4, 18), "speed_kph": max(12, 58 - traffic // 2),
    }


def enrich_with_weather(metrics: dict[str, Any], point: tuple[float, float]) -> dict[str, Any]:
    if not settings.OPENWEATHER_API_KEY:
        return metrics
    try:
        response = requests.get("https://api.openweathermap.org/data/2.5/weather", params={"lat": point[1], "lon": point[0], "appid": settings.OPENWEATHER_API_KEY, "units": "metric"}, timeout=5)
        response.raise_for_status()
        data = response.json()
        metrics.update({"source": "openweathermap", "temperature_c": data["main"]["temp"], "humidity_percent": data["main"]["humidity"], "wind_speed_kph": round(data["wind"].get("speed", 0) * 3.6, 1), "weather_description": data["weather"][0]["description"]})
    except (requests.RequestException, KeyError, IndexError, ValueError):
        pass
    return metrics


def enrich_with_aqi(metrics: dict[str, Any], point: tuple[float, float]) -> dict[str, Any]:
    """Use WAQI when configured; retain traceable demo values when it is unavailable."""
    if not settings.WAQI_TOKEN:
        return metrics
    try:
        response = requests.get(f"https://api.waqi.info/feed/geo:{point[1]};{point[0]}/", params={"token": settings.WAQI_TOKEN}, timeout=5)
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "ok" and isinstance(data.get("data", {}).get("aqi"), (int, float)):
            aqi = round(data["data"]["aqi"])
            metrics.update({"source": "waqi", "aqi_average": aqi, "aqi_maximum": aqi})
    except (requests.RequestException, KeyError, TypeError, ValueError):
        pass
    return metrics


def enrich_with_traffic(metrics: dict[str, Any], point: tuple[float, float]) -> dict[str, Any]:
    """TomTom Flow Segment Data adapter. The API key is never exposed to Flutter."""
    if not settings.TRAFFIC_API_KEY:
        return metrics
    try:
        response = requests.get("https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json", params={"key": settings.TRAFFIC_API_KEY, "point": f"{point[1]},{point[0]}"}, timeout=5)
        response.raise_for_status()
        flow = response.json()["flowSegmentData"]
        ratio = flow["currentSpeed"] / max(1, flow["freeFlowSpeed"])
        score = round(max(0, min(100, 100 - ratio * 100)))
        level = "Low" if score < 35 else "Moderate" if score < 60 else "Heavy" if score < 80 else "Severe"
        metrics.update({"source": "tomtom", "traffic_score": score, "traffic_level": level, "speed_kph": round(flow["currentSpeed"]), "traffic_delay_minutes": max(0, round(metrics["traffic_delay_minutes"] * (1 + score / 100)))})
    except (requests.RequestException, KeyError, TypeError, ValueError, ZeroDivisionError):
        pass
    return metrics


def aqi_category(aqi: int) -> str:
    if aqi <= 50: return "Good"
    if aqi <= 100: return "Moderate"
    if aqi <= 150: return "Unhealthy"
    if aqi <= 200: return "Very Unhealthy"
    return "Hazardous"


def build_recommendations(source_label: str, destination_label: str) -> dict[str, Any]:
    origin, destination = resolve_location(source_label), resolve_location(destination_label)
    candidates = generate_routes(origin, destination)
    predictor = NoisePredictor()
    ranked: list[dict[str, Any]] = []
    for index, candidate in enumerate(candidates):
        midpoint = tuple(candidate.coordinates[len(candidate.coordinates) // 2])
        metrics = enrich_with_traffic(enrich_with_aqi(enrich_with_weather(demo_metrics(candidate, index), midpoint), midpoint), midpoint)
        noise = predictor.predict(metrics["traffic_score"], metrics["motorcycle_share"], metrics["bus_share"], metrics["speed_kph"], metrics["rain_probability"])
        risk = calculate_risk(metrics["aqi_average"], noise.decibels, metrics["traffic_score"], metrics["weather_impact_score"])
        ranked.append({"route": candidate, "metrics": metrics, "noise": noise, "risk": risk})
    balanced = min(ranked, key=lambda item: item["risk"].total)
    fastest = min(ranked, key=lambda item: item["route"].duration_minutes)
    cleanest = min(ranked, key=lambda item: item["metrics"]["aqi_average"])
    quietest = min(ranked, key=lambda item: item["noise"].decibels)
    for item in ranked:
        recommendations = []
        if item is balanced: recommendations.append("Balanced EcoRoute")
        if item is fastest: recommendations.append("Fastest Route")
        if item is cleanest: recommendations.append("Cleanest Route")
        if item is quietest: recommendations.append("Quietest Route")
        item["recommendations"] = recommendations
    return {"source": {"label": source_label, "coordinates": [origin[1], origin[0]]}, "destination": {"label": destination_label, "coordinates": [destination[1], destination[0]]}, "routes": ranked}


@transaction.atomic
def persist_recommendations(result: dict[str, Any]) -> list[dict[str, Any]]:
    source = result["source"]
    destination = result["destination"]
    source_lon, source_lat = source["coordinates"][1], source["coordinates"][0]
    destination_lon, destination_lat = destination["coordinates"][1], destination["coordinates"][0]
    search = RouteSearch.objects.create(source_label=source["label"], destination_label=destination["label"], source=Point(source_lon, source_lat), destination=Point(destination_lon, destination_lat))
    serialized = []
    for item in result["routes"]:
        candidate, metrics, noise, risk = item["route"], item["metrics"], item["noise"], item["risk"]
        route = Route.objects.create(search=search, name=candidate.name, geometry=LineString(*candidate.coordinates), distance_km=candidate.distance_km, duration_minutes=candidate.duration_minutes, road_segments=candidate.road_segments)
        EnvironmentalReading.objects.create(route=route, provider=metrics["source"], aqi_average=metrics["aqi_average"], aqi_maximum=metrics["aqi_maximum"], traffic_score=metrics["traffic_score"], traffic_level=metrics["traffic_level"], traffic_delay_minutes=metrics["traffic_delay_minutes"], temperature_c=metrics["temperature_c"], humidity_percent=metrics["humidity_percent"], wind_speed_kph=metrics["wind_speed_kph"], rain_probability=metrics["rain_probability"], weather_description=metrics["weather_description"], weather_impact_score=metrics["weather_impact_score"])
        prediction = NoisePrediction.objects.create(route=route, model_version=noise.model_version, predicted_db=noise.decibels, input_features={key: metrics[key] for key in ("traffic_score", "motorcycle_share", "bus_share", "speed_kph", "rain_probability")})
        SHAPExplanation.objects.create(prediction=prediction, contributors=noise.contributors, user_summary=noise.summary)
        RouteScore.objects.create(route=route, aqi_score=risk.aqi, noise_score=risk.noise, traffic_score=risk.traffic, weather_score=risk.weather, environmental_risk_score=risk.total, category=risk.category, is_recommended="Balanced EcoRoute" in item["recommendations"])
        serialized.append({"id": str(route.id), "name": candidate.name, "coordinates": candidate.coordinates, "distance_km": candidate.distance_km, "duration_minutes": candidate.duration_minutes, "road_segments": candidate.road_segments, "aqi": {"average": metrics["aqi_average"], "maximum": metrics["aqi_maximum"], "category": aqi_category(metrics["aqi_average"])}, "traffic": {"score": metrics["traffic_score"], "level": metrics["traffic_level"], "delay_minutes": metrics["traffic_delay_minutes"]}, "weather": {"temperature_c": metrics["temperature_c"], "humidity_percent": metrics["humidity_percent"], "wind_speed_kph": metrics["wind_speed_kph"], "rain_probability": metrics["rain_probability"], "description": metrics["weather_description"], "impact_score": metrics["weather_impact_score"]}, "noise": {"decibels": noise.decibels, "model_version": noise.model_version, "contributors": noise.contributors, "explanation": noise.summary}, "risk": asdict(risk), "recommendations": item["recommendations"]})
    return serialized
