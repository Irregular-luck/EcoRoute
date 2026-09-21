# EcoRoute architecture

```mermaid
flowchart LR
  A[Flutter Android app] -->|POST /api/routes| B[Django REST API]
  B --> C[OSRM / OpenStreetMap]
  B --> D[AQI provider]
  B --> E[Traffic provider]
  B --> F[OpenWeatherMap]
  B --> G[Noise LSTM + SHAP]
  D --> H[Environmental risk engine]
  E --> H
  F --> H
  G --> H
  H --> I[(PostgreSQL + PostGIS)]
  H --> B
  B --> A
  J[Celery + Redis] -->|refresh/cache tasks| B
```

The API owns provider-specific adaptation, validates route input, records the sampled inputs and outputs, and returns ranked routes in a mobile-friendly response. Provider calls must be cached by coordinate/time bucket in production to respect quotas.

## Environmental score

All components are normalized to 0–100 before the final score:

`risk = 0.35 × AQI + 0.25 × noise + 0.25 × traffic + 0.15 × weather`

Scores of 0–30 are Safe, 31–60 Moderate, and 61–100 High Risk. Lower is better.

## Data model

```mermaid
erDiagram
  ROUTE_SEARCH ||--o{ ROUTE : produces
  ROUTE ||--o{ ENVIRONMENTAL_READING : samples
  ROUTE ||--|| NOISE_PREDICTION : has
  NOISE_PREDICTION ||--|| SHAP_EXPLANATION : explains
  ROUTE ||--|| ROUTE_SCORE : receives
  USER ||--o{ SAVED_ROUTE : saves
  ROUTE ||--o{ SAVED_ROUTE : is_saved
  ROUTE_SEARCH {
    uuid id PK
    point source
    point destination
  }
  ROUTE {
    uuid id PK
    linestring geometry
    decimal distance_km
  }
  ENVIRONMENTAL_READING {
    int aqi_average
    int traffic_score
    int weather_impact_score
  }
  NOISE_PREDICTION {
    decimal predicted_db
    json input_features
  }
  ROUTE_SCORE {
    int environmental_risk_score
    string category
  }
```

## ML lifecycle

Use `backend/ml/train_noise.py` with timestamp-ordered, road-segment-labelled observations. It uses a sequence LSTM, saves a Keras artifact plus scaler, and exposes a SHAP GradientExplainer adapter. Register a model version, its evaluation metrics, and the data window before promoting it. The API deliberately serves a labelled deterministic baseline until a trained artifact is present; it does not claim demo estimates are LSTM inference.
