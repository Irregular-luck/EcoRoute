# Generated from the initial EcoRoute domain model.
import uuid
from django.conf import settings
from django.contrib.gis.db.models import fields as gis_fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="RouteSearch",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("source_label", models.CharField(max_length=255)),
                ("destination_label", models.CharField(max_length=255)),
                ("source", gis_fields.PointField(geography=True, srid=4326)),
                ("destination", gis_fields.PointField(geography=True, srid=4326)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="Route",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=64)),
                ("geometry", gis_fields.LineStringField(geography=True, srid=4326)),
                ("distance_km", models.DecimalField(decimal_places=2, max_digits=7)),
                ("duration_minutes", models.PositiveIntegerField()),
                ("road_segments", models.JSONField(default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("search", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="routes", to="routes.routesearch")),
            ],
        ),
        migrations.CreateModel(
            name="RouteScore",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("aqi_score", models.PositiveSmallIntegerField()),
                ("noise_score", models.PositiveSmallIntegerField()),
                ("traffic_score", models.PositiveSmallIntegerField()),
                ("weather_score", models.PositiveSmallIntegerField()),
                ("environmental_risk_score", models.PositiveSmallIntegerField()),
                ("category", models.CharField(max_length=16)),
                ("is_recommended", models.BooleanField(default=False)),
                ("route", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="score", to="routes.route")),
            ],
        ),
        migrations.CreateModel(
            name="NoisePrediction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("model_version", models.CharField(max_length=64)),
                ("predicted_db", models.DecimalField(decimal_places=1, max_digits=5)),
                ("input_features", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("route", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="noise_prediction", to="routes.route")),
            ],
        ),
        migrations.CreateModel(
            name="EnvironmentalReading",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider", models.CharField(max_length=32)),
                ("aqi_average", models.PositiveIntegerField()),
                ("aqi_maximum", models.PositiveIntegerField()),
                ("traffic_score", models.PositiveSmallIntegerField()),
                ("traffic_level", models.CharField(max_length=16)),
                ("traffic_delay_minutes", models.PositiveIntegerField(default=0)),
                ("temperature_c", models.DecimalField(decimal_places=1, max_digits=5)),
                ("humidity_percent", models.PositiveSmallIntegerField()),
                ("wind_speed_kph", models.DecimalField(decimal_places=1, max_digits=5)),
                ("rain_probability", models.PositiveSmallIntegerField()),
                ("weather_description", models.CharField(max_length=64)),
                ("weather_impact_score", models.PositiveSmallIntegerField()),
                ("sampled_at", models.DateTimeField(auto_now_add=True)),
                ("route", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="readings", to="routes.route")),
            ],
        ),
        migrations.CreateModel(
            name="SHAPExplanation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("contributors", models.JSONField(default=list)),
                ("user_summary", models.TextField()),
                ("prediction", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="explanation", to="routes.noiseprediction")),
            ],
        ),
        migrations.CreateModel(
            name="SavedRoute",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nickname", models.CharField(blank=True, max_length=64)),
                ("saved_at", models.DateTimeField(auto_now_add=True)),
                ("route", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="routes.route")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={"constraints": [models.UniqueConstraint(fields=("user", "route"), name="unique_saved_route")]},
        ),
    ]
