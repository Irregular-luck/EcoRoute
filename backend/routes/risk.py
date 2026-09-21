from dataclasses import dataclass


@dataclass(frozen=True)
class RiskBreakdown:
    aqi: int
    noise: int
    traffic: int
    weather: int
    total: int
    category: str


def clamp(value: float) -> int:
    return round(max(0, min(100, value)))


def aqi_to_risk(aqi: float) -> int:
    # AQI 0..300 maps to a 0..100 exposure scale, capped beyond hazardous.
    return clamp(aqi / 3)


def noise_to_risk(decibels: float) -> int:
    # 45 dB is quiet urban ambient; 95 dB is high sustained exposure.
    return clamp((decibels - 45) * 2)


def calculate_risk(aqi: float, noise_db: float, traffic: float, weather: float) -> RiskBreakdown:
    aqi_score, noise_score = aqi_to_risk(aqi), noise_to_risk(noise_db)
    traffic_score, weather_score = clamp(traffic), clamp(weather)
    total = clamp(.35 * aqi_score + .25 * noise_score + .25 * traffic_score + .15 * weather_score)
    category = "Safe" if total <= 30 else "Moderate" if total <= 60 else "High Risk"
    return RiskBreakdown(aqi_score, noise_score, traffic_score, weather_score, total, category)
