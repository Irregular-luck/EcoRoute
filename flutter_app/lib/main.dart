import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:latlong2/latlong.dart';

import 'api.dart';
import 'models.dart';

final apiProvider = Provider<EcoRouteApi>((ref) => EcoRouteApi());
final routeSearchProvider =
    StateNotifierProvider<RouteSearchController, AsyncValue<RouteResponse?>>(
  (ref) => RouteSearchController(ref.read(apiProvider)),
);

class RouteSearchController extends StateNotifier<AsyncValue<RouteResponse?>> {
  RouteSearchController(this._api) : super(const AsyncData(null));
  final EcoRouteApi _api;

  Future<void> find(String source, String destination) async {
    state = const AsyncLoading();
    try {
      state = AsyncData(await _api.findRoutes(source, destination));
    } catch (error, stackTrace) {
      state = AsyncError(error, stackTrace);
    }
  }
}

void main() => runApp(const ProviderScope(child: EcoRouteApp()));

class EcoRouteApp extends StatelessWidget {
  const EcoRouteApp({super.key});

  @override
  Widget build(BuildContext context) {
    const seed = Color(0xff1B8A5A);
    return MaterialApp(
      title: 'EcoRoute',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: seed,
          brightness: Brightness.light,
        ),
        useMaterial3: true,
      ),
      darkTheme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: seed,
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
      ),
      themeMode: ThemeMode.system,
      home: const HomeScreen(),
    );
  }
}

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  final _source = TextEditingController(text: 'Bengaluru');
  final _destination = TextEditingController(text: 'Indiranagar');
  bool _openingResult = false;

  @override
  void dispose() {
    _source.dispose();
    _destination.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    ref.listen<AsyncValue<RouteResponse?>>(routeSearchProvider, (
      previous,
      next,
    ) {
      final result = next.valueOrNull;
      if (result != null && !_openingResult) {
        _openingResult = true;
        Navigator.of(context)
            .push(
              MaterialPageRoute(builder: (_) => ResultsScreen(result: result)),
            )
            .then((_) => _openingResult = false);
      }
      next.whenOrNull(
        error: (error, _) => ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Could not analyse routes: $error')),
        ),
      );
    });
    final loading = ref.watch(routeSearchProvider).isLoading;
    final colors = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(
        title: const Text('EcoRoute'),
        actions: [
          IconButton(
            tooltip: 'About EcoRoute',
            icon: const Icon(Icons.info_outline),
            onPressed: () => showAboutDialog(
              context: context,
              applicationName: 'EcoRoute',
              applicationVersion: '1.0.0',
              children: const [
                Text(
                  'Healthier journeys, informed by air, noise, traffic and weather.',
                ),
              ],
            ),
          ),
        ],
      ),
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 620),
            child: ListView(
              padding: const EdgeInsets.all(24),
              children: [
                Container(
                  padding: const EdgeInsets.all(24),
                  decoration: BoxDecoration(
                    color: colors.primaryContainer,
                    borderRadius: BorderRadius.circular(28),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Icon(Icons.eco_rounded, size: 52, color: colors.primary),
                      const SizedBox(height: 14),
                      Text(
                        'A healthier way to move.',
                        style: Theme.of(context)
                            .textTheme
                            .headlineSmall
                            ?.copyWith(fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        'Compare route exposure to air pollution, traffic, weather and predicted noise before you leave.',
                        style: Theme.of(context).textTheme.bodyLarge,
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 28),
                _LocationField(
                  controller: _source,
                  label: 'From',
                  icon: Icons.trip_origin_rounded,
                ),
                Align(
                  alignment: Alignment.centerRight,
                  child: IconButton.filledTonal(
                    tooltip: 'Swap locations',
                    icon: const Icon(Icons.swap_vert_rounded),
                    onPressed: () => setState(() {
                      final current = _source.text;
                      _source.text = _destination.text;
                      _destination.text = current;
                    }),
                  ),
                ),
                _LocationField(
                  controller: _destination,
                  label: 'To',
                  icon: Icons.location_on_rounded,
                ),
                const SizedBox(height: 16),
                OutlinedButton.icon(
                  onPressed: _setCurrentLocation,
                  icon: const Icon(Icons.my_location),
                  label: const Text('Use current location'),
                ),
                const SizedBox(height: 12),
                FilledButton.icon(
                  style: FilledButton.styleFrom(
                    minimumSize: const Size.fromHeight(54),
                  ),
                  onPressed: loading
                      ? null
                      : () => ref.read(routeSearchProvider.notifier).find(
                            _source.text.trim(),
                            _destination.text.trim(),
                          ),
                  icon: loading
                      ? const SizedBox.square(
                          dimension: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.auto_awesome),
                  label: Text(
                    loading ? 'Analysing environment…' : 'Find EcoRoute',
                  ),
                ),
                const SizedBox(height: 20),
                const _MetricLegend(),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _setCurrentLocation() async {
    if (!await Geolocator.isLocationServiceEnabled()) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'Turn on location services to use your current position.',
            ),
          ),
        );
      }
      return;
    }
    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }
    if (permission == LocationPermission.denied ||
        permission == LocationPermission.deniedForever) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'EcoRoute needs location permission to set your start point.',
            ),
          ),
        );
      }
      return;
    }
    final position = await Geolocator.getCurrentPosition();
    if (mounted) {
      setState(
        () => _source.text =
            '${position.latitude.toStringAsFixed(6)},${position.longitude.toStringAsFixed(6)}',
      );
    }
  }
}

class _LocationField extends StatelessWidget {
  const _LocationField({
    required this.controller,
    required this.label,
    required this.icon,
  });
  final TextEditingController controller;
  final String label;
  final IconData icon;
  @override
  Widget build(BuildContext context) => TextField(
        controller: controller,
        textInputAction: TextInputAction.next,
        decoration: InputDecoration(
          labelText: label,
          prefixIcon: Icon(icon),
          border: const OutlineInputBorder(),
        ),
      );
}

class _MetricLegend extends StatelessWidget {
  const _MetricLegend();
  @override
  Widget build(BuildContext context) => Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              const Icon(Icons.shield_outlined),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  'EcoRoute ranks lower environmental exposure first. Green is safer; amber is moderate; red needs care.',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              ),
            ],
          ),
        ),
      );
}

class ResultsScreen extends StatelessWidget {
  const ResultsScreen({super.key, required this.result});
  final RouteResponse result;

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: const Text('Route recommendations'),
          actions: [
            IconButton(
              tooltip: 'Analytics',
              icon: const Icon(Icons.insights_outlined),
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute(
                    builder: (_) => AnalyticsScreen(result: result)),
              ),
            ),
          ],
        ),
        body: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            if (result.isDemo) const _DemoNotice(),
            Text(
              '${result.source.label}  →  ${result.destination.label}',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 12),
            ...result.routes.map(
              (route) => _RouteCard(
                route: route,
                allRoutes: result.routes,
                source: result.source,
                destination: result.destination,
              ),
            ),
          ],
        ),
      );
}

class _DemoNotice extends StatelessWidget {
  const _DemoNotice();
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: MaterialBanner(
          content: const Text(
            'Showing clearly labelled demo estimates. Start the API to use live route analysis.',
          ),
          actions: [TextButton(onPressed: () {}, child: const Text('OK'))],
        ),
      );
}

class _RouteCard extends StatelessWidget {
  const _RouteCard({
    required this.route,
    required this.allRoutes,
    required this.source,
    required this.destination,
  });
  final RouteInfo route;
  final List<RouteInfo> allRoutes;
  final Endpoint source;
  final Endpoint destination;

  @override
  Widget build(BuildContext context) {
    final color = _riskColor(route.risk.total);
    return Card(
      margin: const EdgeInsets.only(bottom: 14),
      clipBehavior: Clip.antiAlias,
      child: Column(
        children: [
          ListTile(
            tileColor: route.recommended
                ? Theme.of(context).colorScheme.primaryContainer
                : null,
            title: Row(
              children: [
                Text(
                  route.name,
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
                if (route.recommended)
                  const Padding(
                    padding: EdgeInsets.only(left: 8),
                    child: Chip(label: Text('Recommended')),
                  ),
              ],
            ),
            subtitle: Text(
              '${route.distanceKm.toStringAsFixed(1)} km  •  ${route.durationMinutes} min  •  ${route.traffic.delayMinutes} min delay',
            ),
            trailing: _RiskBadge(score: route.risk.total, color: color),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
            child: Column(
              children: [
                Row(
                  children: [
                    Expanded(
                      child: _Fact(
                        icon: Icons.air,
                        label: 'AQI',
                        value: '${route.aqi.average}',
                      ),
                    ),
                    Expanded(
                      child: _Fact(
                        icon: Icons.volume_up_outlined,
                        label: 'Noise',
                        value: '${route.noise.decibels.toStringAsFixed(0)} dB',
                      ),
                    ),
                    Expanded(
                      child: _Fact(
                        icon: Icons.cloud_outlined,
                        label: 'Weather',
                        value:
                            '${route.weather.temperature.toStringAsFixed(0)}°C',
                      ),
                    ),
                  ],
                ),
                if (route.recommendations.isNotEmpty)
                  Align(
                    alignment: Alignment.centerLeft,
                    child: Wrap(
                      spacing: 6,
                      children: route.recommendations
                          .map((label) => Chip(label: Text(label)))
                          .toList(),
                    ),
                  ),
                const SizedBox(height: 4),
                Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    route.noise.explanation,
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        icon: const Icon(Icons.map_outlined),
                        label: const Text('View on map'),
                        onPressed: () => Navigator.of(context).push(
                          MaterialPageRoute(
                            builder: (_) => EcoMapScreen(
                              routes: allRoutes,
                              source: source,
                              destination: destination,
                              selected: route,
                            ),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    IconButton.filledTonal(
                      tooltip: 'Route details',
                      icon: const Icon(Icons.chevron_right),
                      onPressed: () => _showDetails(context, route),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

void _showDetails(
  BuildContext context,
  RouteInfo route,
) =>
    showModalBottomSheet(
      context: context,
      showDragHandle: true,
      builder: (_) => Padding(
        padding: const EdgeInsets.fromLTRB(24, 0, 24, 36),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '${route.name} · Environmental profile',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            ...route.noise.contributors.map(
              (c) => ListTile(
                dense: true,
                contentPadding: EdgeInsets.zero,
                leading: Icon(
                  c.impactDb >= 0
                      ? Icons.add_circle_outline
                      : Icons.remove_circle_outline,
                ),
                title: Text(c.feature),
                trailing: Text(
                  '${c.impactDb >= 0 ? '+' : ''}${c.impactDb.toStringAsFixed(1)} dB',
                ),
              ),
            ),
            const Divider(),
            Text(
              'Risk composition: AQI ${route.risk.aqi} · Noise ${route.risk.noise} · Traffic ${route.risk.traffic} · Weather ${route.risk.weather}',
            ),
          ],
        ),
      ),
    );

class _Fact extends StatelessWidget {
  const _Fact({required this.icon, required this.label, required this.value});
  final IconData icon;
  final String label;
  final String value;
  @override
  Widget build(BuildContext context) => Row(
        children: [
          Icon(icon, size: 18),
          const SizedBox(width: 4),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(value, style: const TextStyle(fontWeight: FontWeight.w600)),
              Text(label, style: Theme.of(context).textTheme.labelSmall),
            ],
          ),
        ],
      );
}

class _RiskBadge extends StatelessWidget {
  const _RiskBadge({required this.score, required this.color});
  final int score;
  final Color color;
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: color.withOpacity(.15),
          borderRadius: BorderRadius.circular(16),
        ),
        child: Text(
          '$score\nRisk',
          textAlign: TextAlign.center,
          style: TextStyle(color: color, fontWeight: FontWeight.bold),
        ),
      );
}

Color _riskColor(int risk) => risk <= 30
    ? Colors.green.shade700
    : risk <= 60
        ? Colors.orange.shade800
        : Colors.red.shade700;

class EcoMapScreen extends StatefulWidget {
  const EcoMapScreen({
    super.key,
    required this.routes,
    required this.source,
    required this.destination,
    required this.selected,
  });
  final List<RouteInfo> routes;
  final Endpoint source;
  final Endpoint destination;
  final RouteInfo selected;

  @override
  State<EcoMapScreen> createState() => _EcoMapScreenState();
}

enum MapLayer { routes, aqi, traffic, noise, risk }

class _EcoMapScreenState extends State<EcoMapScreen> {
  late RouteInfo _selected = widget.selected;
  MapLayer _layer = MapLayer.routes;

  @override
  Widget build(BuildContext context) {
    final center = LatLng(
      widget.source.coordinates[0],
      widget.source.coordinates[1],
    );
    return Scaffold(
      appBar: AppBar(title: const Text('Environmental map')),
      body: Stack(
        children: [
          FlutterMap(
            options: MapOptions(initialCenter: center, initialZoom: 13),
            children: [
              TileLayer(
                urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                userAgentPackageName: 'com.ecoroute.app',
              ),
              PolylineLayer(
                polylines: widget.routes
                    .map(
                      (route) => Polyline(
                        points: route.coordinates
                            .map((point) => LatLng(point[1], point[0]))
                            .toList(),
                        color: route.id == _selected.id
                            ? _riskColor(route.risk.total)
                            : Colors.blueGrey.withOpacity(.55),
                        strokeWidth: route.id == _selected.id ? 6 : 3,
                      ),
                    )
                    .toList(),
              ),
              if (_layer != MapLayer.routes)
                CircleLayer(circles: _overlayPoints()),
              MarkerLayer(
                markers: [
                  _marker(
                    widget.source,
                    Icons.trip_origin,
                    Colors.green.shade700,
                  ),
                  _marker(
                    widget.destination,
                    Icons.location_on,
                    Colors.red.shade700,
                  ),
                ],
              ),
            ],
          ),
          Positioned(
            top: 12,
            left: 12,
            right: 12,
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: SegmentedButton<MapLayer>(
                segments: const [
                  ButtonSegment(
                    value: MapLayer.routes,
                    icon: Icon(Icons.route),
                    label: Text('Routes'),
                  ),
                  ButtonSegment(
                    value: MapLayer.aqi,
                    icon: Icon(Icons.air),
                    label: Text('AQI'),
                  ),
                  ButtonSegment(
                    value: MapLayer.traffic,
                    icon: Icon(Icons.traffic),
                    label: Text('Traffic'),
                  ),
                  ButtonSegment(
                    value: MapLayer.noise,
                    icon: Icon(Icons.volume_up),
                    label: Text('Noise'),
                  ),
                  ButtonSegment(
                    value: MapLayer.risk,
                    icon: Icon(Icons.shield),
                    label: Text('Risk'),
                  ),
                ],
                selected: {_layer},
                onSelectionChanged: (value) =>
                    setState(() => _layer = value.first),
              ),
            ),
          ),
          Positioned(
            left: 12,
            right: 12,
            bottom: 16,
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    DropdownButton<RouteInfo>(
                      isExpanded: true,
                      value: _selected,
                      items: widget.routes
                          .map(
                            (route) => DropdownMenuItem(
                              value: route,
                              child: Text(
                                '${route.name} · ${route.risk.total} risk',
                              ),
                            ),
                          )
                          .toList(),
                      onChanged: (value) => setState(() => _selected = value!),
                    ),
                    Row(
                      children: [
                        Container(
                          width: 10,
                          height: 10,
                          decoration: BoxDecoration(
                            color: Colors.green.shade700,
                            shape: BoxShape.circle,
                          ),
                        ),
                        const SizedBox(width: 5),
                        const Text('Safe'),
                        const SizedBox(width: 12),
                        Container(
                          width: 10,
                          height: 10,
                          decoration: BoxDecoration(
                            color: Colors.orange.shade800,
                            shape: BoxShape.circle,
                          ),
                        ),
                        const SizedBox(width: 5),
                        const Text('Moderate'),
                        const SizedBox(width: 12),
                        Container(
                          width: 10,
                          height: 10,
                          decoration: BoxDecoration(
                            color: Colors.red.shade700,
                            shape: BoxShape.circle,
                          ),
                        ),
                        const SizedBox(width: 5),
                        const Text('High exposure'),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Marker _marker(Endpoint location, IconData icon, Color color) => Marker(
        point: LatLng(location.coordinates[0], location.coordinates[1]),
        width: 42,
        height: 42,
        child: Icon(icon, color: color, size: 34),
      );

  List<CircleMarker> _overlayPoints() {
    return _selected.coordinates.map((point) {
      final amount = switch (_layer) {
        MapLayer.aqi => _selected.aqi.average,
        MapLayer.traffic => _selected.traffic.score,
        MapLayer.noise => _selected.risk.noise,
        MapLayer.risk => _selected.risk.total,
        MapLayer.routes => 0,
      };
      return CircleMarker(
        point: LatLng(point[1], point[0]),
        radius: 18,
        color: _riskColor(amount).withOpacity(.38),
        borderStrokeWidth: 1,
        borderColor: _riskColor(amount),
      );
    }).toList();
  }
}

class AnalyticsScreen extends StatelessWidget {
  const AnalyticsScreen({super.key, required this.result});
  final RouteResponse result;

  @override
  Widget build(BuildContext context) {
    final safest = result.routes.reduce(
      (a, b) => a.risk.total < b.risk.total ? a : b,
    );
    return Scaffold(
      appBar: AppBar(title: const Text('Exposure analytics')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            'Today’s route comparison',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 12),
          Card(
            child: SizedBox(
              height: 210,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 22, 20, 12),
                child: LineChart(
                  LineChartData(
                    gridData: const FlGridData(show: true),
                    titlesData: const FlTitlesData(show: true),
                    borderData: FlBorderData(show: false),
                    minY: 0,
                    maxY: 100,
                    lineBarsData: [
                      LineChartBarData(
                        isCurved: true,
                        color: Theme.of(context).colorScheme.primary,
                        barWidth: 4,
                        dotData: const FlDotData(show: true),
                        belowBarData: BarAreaData(
                          show: true,
                          color: Theme.of(context)
                              .colorScheme
                              .primary
                              .withOpacity(.14),
                        ),
                        spots: result.routes
                            .asMap()
                            .entries
                            .map(
                              (entry) => FlSpot(
                                entry.key.toDouble(),
                                entry.value.risk.total.toDouble(),
                              ),
                            )
                            .toList(),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: 14),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Environmental exposure summary',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 10),
                  Text(
                    '${safest.name} is the lower-exposure option at ${safest.risk.total}/100 risk. It has AQI ${safest.aqi.average} and predicted noise of ${safest.noise.decibels.toStringAsFixed(0)} dB.',
                  ),
                  const SizedBox(height: 12),
                  FilledButton.tonalIcon(
                    onPressed: () => ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text(
                          'Report export is available once route history is connected to a signed-in account.',
                        ),
                      ),
                    ),
                    icon: const Icon(Icons.ios_share_outlined),
                    label: const Text('Export report'),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 14),
          ...result.routes.map(
            (route) => Card(
              child: ListTile(
                leading: CircleAvatar(
                  backgroundColor:
                      _riskColor(route.risk.total).withOpacity(.14),
                  child: Text(
                    '${route.risk.total}',
                    style: TextStyle(
                      color: _riskColor(route.risk.total),
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                title: Text(route.name),
                subtitle: Text(
                  'AQI ${route.aqi.average} · ${route.noise.decibels.toStringAsFixed(0)} dB · ${route.traffic.level} traffic',
                ),
                trailing: Text(route.risk.category),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
