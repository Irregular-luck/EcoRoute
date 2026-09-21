import 'package:dio/dio.dart';

import 'models.dart';

class EcoRouteApi {
  EcoRouteApi()
      : _client = Dio(
          BaseOptions(
            baseUrl: const String.fromEnvironment(
              'API_BASE_URL',
              defaultValue: 'http://10.0.2.2:8000/api',
            ),
            connectTimeout: const Duration(seconds: 8),
            receiveTimeout: const Duration(seconds: 12),
          ),
        );
  final Dio _client;

  Future<RouteResponse> findRoutes(String source, String destination) async {
    try {
      final response = await _client.post<Map<String, dynamic>>(
        '/routes',
        data: {'source': source, 'destination': destination},
      );
      return RouteResponse.fromJson(response.data!);
    } on DioException {
      return _demoResponse(source, destination);
    }
  }

  RouteResponse _demoResponse(String source, String destination) {
    final start = Endpoint(
      label: source,
      coordinates: const [12.9716, 77.5946],
    );
    final end = Endpoint(
      label: destination,
      coordinates: const [12.9784, 77.6408],
    );
    RouteInfo make(
      String id,
      String name,
      double distance,
      int mins,
      int aqi,
      int traffic,
      double db,
      int risk,
      List<String> badges,
      List<List<double>> points,
    ) =>
        RouteInfo(
          id: id,
          name: name,
          coordinates: points,
          distanceKm: distance,
          durationMinutes: mins,
          aqi: Aqi(aqi, aqi + 14, aqi < 51 ? 'Good' : 'Moderate'),
          traffic: Traffic(
            traffic,
            traffic < 40 ? 'Low' : 'Moderate',
            traffic ~/ 10,
          ),
          weather: const Weather(28, 58, 12, 18, 'partly cloudy', 19),
          noise: Noise(
            db,
            'This route is noisy because of traffic density and motorcycle share.',
            [
              NoiseContributor('Traffic density', traffic * .22),
              const NoiseContributor('Motorcycle share', 4.2),
              const NoiseContributor('Average speed', -1.7),
            ],
          ),
          risk: Risk(
            risk,
            risk < 31 ? 'Safe' : 'Moderate',
            aqi ~/ 3,
            ((db - 45) * 2).round(),
            traffic,
            19,
          ),
          recommendations: badges,
        );
    return RouteResponse(
      source: start,
      destination: end,
      isDemo: true,
      routes: [
        make(
          'a',
          'Route A',
          5.8,
          19,
          82,
          63,
          69,
          49,
          ['Fastest Route'],
          const [
            [77.5946, 12.9716],
            [77.615, 12.968],
            [77.6408, 12.9784],
          ],
        ),
        make(
          'b',
          'Route B',
          6.6,
          24,
          54,
          35,
          60,
          31,
          ['Balanced EcoRoute', 'Cleanest Route', 'Quietest Route'],
          const [
            [77.5946, 12.9716],
            [77.612, 12.990],
            [77.6408, 12.9784],
          ],
        ),
        make('c', 'Route C', 7.1, 26, 105, 49, 72, 57, const [], const [
          [77.5946, 12.9716],
          [77.621, 12.954],
          [77.6408, 12.9784],
        ]),
      ],
    );
  }
}
