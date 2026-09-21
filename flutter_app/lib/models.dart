class RouteResponse {
  const RouteResponse({
    required this.source,
    required this.destination,
    required this.routes,
    this.isDemo = false,
  });

  final Endpoint source;
  final Endpoint destination;
  final List<RouteInfo> routes;
  final bool isDemo;

  factory RouteResponse.fromJson(Map<String, dynamic> json) => RouteResponse(
        source: Endpoint.fromJson(json['source'] as Map<String, dynamic>),
        destination:
            Endpoint.fromJson(json['destination'] as Map<String, dynamic>),
        routes: (json['routes'] as List<dynamic>)
            .map((e) => RouteInfo.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

class Endpoint {
  const Endpoint({required this.label, required this.coordinates});
  final String label;
  final List<double> coordinates; // [latitude, longitude]
  factory Endpoint.fromJson(Map<String, dynamic> json) => Endpoint(
        label: json['label'] as String,
        coordinates: (json['coordinates'] as List<dynamic>)
            .map((e) => (e as num).toDouble())
            .toList(),
      );
}

class RouteInfo {
  const RouteInfo({
    required this.id,
    required this.name,
    required this.coordinates,
    required this.distanceKm,
    required this.durationMinutes,
    required this.aqi,
    required this.traffic,
    required this.weather,
    required this.noise,
    required this.risk,
    required this.recommendations,
  });
  final String id;
  final String name;
  final List<List<double>> coordinates; // [[longitude, latitude]]
  final double distanceKm;
  final int durationMinutes;
  final Aqi aqi;
  final Traffic traffic;
  final Weather weather;
  final Noise noise;
  final Risk risk;
  final List<String> recommendations;

  bool get recommended => recommendations.contains('Balanced EcoRoute');
  factory RouteInfo.fromJson(Map<String, dynamic> json) => RouteInfo(
        id: json['id'] as String,
        name: json['name'] as String,
        coordinates: (json['coordinates'] as List<dynamic>)
            .map(
              (point) => (point as List<dynamic>)
                  .map((e) => (e as num).toDouble())
                  .toList(),
            )
            .toList(),
        distanceKm: (json['distance_km'] as num).toDouble(),
        durationMinutes: json['duration_minutes'] as int,
        aqi: Aqi.fromJson(json['aqi'] as Map<String, dynamic>),
        traffic: Traffic.fromJson(json['traffic'] as Map<String, dynamic>),
        weather: Weather.fromJson(json['weather'] as Map<String, dynamic>),
        noise: Noise.fromJson(json['noise'] as Map<String, dynamic>),
        risk: Risk.fromJson(json['risk'] as Map<String, dynamic>),
        recommendations:
            (json['recommendations'] as List<dynamic>).cast<String>(),
      );
}

class Aqi {
  const Aqi(this.average, this.maximum, this.category);
  final int average;
  final int maximum;
  final String category;
  factory Aqi.fromJson(Map<String, dynamic> json) => Aqi(
        json['average'] as int,
        json['maximum'] as int,
        json['category'] as String,
      );
}

class Traffic {
  const Traffic(this.score, this.level, this.delayMinutes);
  final int score;
  final String level;
  final int delayMinutes;
  factory Traffic.fromJson(Map<String, dynamic> json) => Traffic(
        json['score'] as int,
        json['level'] as String,
        json['delay_minutes'] as int,
      );
}

class Weather {
  const Weather(
    this.temperature,
    this.humidity,
    this.wind,
    this.rain,
    this.description,
    this.impact,
  );
  final double temperature;
  final int humidity;
  final double wind;
  final int rain;
  final String description;
  final int impact;
  factory Weather.fromJson(Map<String, dynamic> json) => Weather(
        (json['temperature_c'] as num).toDouble(),
        json['humidity_percent'] as int,
        (json['wind_speed_kph'] as num).toDouble(),
        json['rain_probability'] as int,
        json['description'] as String,
        json['impact_score'] as int,
      );
}

class Noise {
  const Noise(this.decibels, this.explanation, this.contributors);
  final double decibels;
  final String explanation;
  final List<NoiseContributor> contributors;
  factory Noise.fromJson(Map<String, dynamic> json) => Noise(
        (json['decibels'] as num).toDouble(),
        json['explanation'] as String,
        (json['contributors'] as List<dynamic>)
            .map((e) => NoiseContributor.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

class NoiseContributor {
  const NoiseContributor(this.feature, this.impactDb);
  final String feature;
  final double impactDb;
  factory NoiseContributor.fromJson(Map<String, dynamic> json) =>
      NoiseContributor(
        json['feature'] as String,
        (json['impact_db'] as num).toDouble(),
      );
}

class Risk {
  const Risk(
    this.total,
    this.category,
    this.aqi,
    this.noise,
    this.traffic,
    this.weather,
  );
  final int total;
  final String category;
  final int aqi;
  final int noise;
  final int traffic;
  final int weather;
  factory Risk.fromJson(Map<String, dynamic> json) => Risk(
        json['total'] as int,
        json['category'] as String,
        json['aqi'] as int,
        json['noise'] as int,
        json['traffic'] as int,
        json['weather'] as int,
      );
}
