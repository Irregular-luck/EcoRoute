# EcoRoute

EcoRoute is an Android-first Flutter application and Django REST API that recommends travel routes by environmental exposure rather than time alone. It scores AQI, traffic, weather, and predicted noise to surface a balanced low-risk route alongside fastest, cleanest, and quietest alternatives.

## What is included

- Flutter Material 3 client with dark mode, route form, results, interactive map, and analytics.
- Django REST API backed by PostgreSQL/PostGIS.
- Provider boundaries for OSRM, OpenAQ/WAQI, traffic, and OpenWeatherMap.
- Noise-prediction adapter with a deployable TensorFlow LSTM model hook and an explainable safe fallback for development.
- Risk engine: `0.35 × AQI + 0.25 × noise + 0.25 × traffic + 0.15 × weather`.
- Docker Compose environment for API, PostGIS, Redis, and Celery worker.

## Quick start

1. Copy `.env.example` to `.env`, add provider keys when available, and set `GEOCODER_USER_AGENT` to identify your app and contact email. The API uses OpenStreetMap Nominatim to convert place names to coordinates.
2. Run `docker compose up --build`.
3. Run the client:

   ```powershell
   cd flutter_app
   flutter pub get
   flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000/api
   ```

For a physical Android device, replace `10.0.2.2` with the LAN IP address of the API host. `flutter create --platforms=android .` can generate any missing platform runner files if this source directory is copied into a fresh Flutter project.

## API

`POST /api/routes` accepts `{ "source": "Bengaluru", "destination": "Indiranagar" }` and returns ranked alternatives. Other endpoints: `POST /api/predict-noise`, `POST /api/calculate-risk`, and `GET /api/aqi`, `/api/traffic`, `/api/weather`, `/api/recommendation`, and `/api/analytics`. JWT tokens are available at `POST /api/auth/token` and `POST /api/auth/token/refresh`.

## Production notes

Provider clients deliberately fail closed into explicit `demo` source data when credentials are absent. Add a reverse proxy/TLS, secret manager, JWT authentication, rate limiting, observability, and provider-specific request limits before public deployment.
