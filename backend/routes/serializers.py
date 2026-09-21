from rest_framework import serializers


class RouteRequestSerializer(serializers.Serializer):
    source = serializers.CharField(max_length=255, trim_whitespace=True)
    destination = serializers.CharField(max_length=255, trim_whitespace=True)

    def validate(self, attrs):
        if attrs["source"].casefold() == attrs["destination"].casefold():
            raise serializers.ValidationError("Source and destination must be different.")
        return attrs


class NoiseRequestSerializer(serializers.Serializer):
    traffic_score = serializers.IntegerField(min_value=0, max_value=100)
    motorcycle_share = serializers.IntegerField(min_value=0, max_value=100)
    bus_share = serializers.IntegerField(min_value=0, max_value=100)
    speed_kph = serializers.IntegerField(min_value=0, max_value=180)
    rain_probability = serializers.IntegerField(min_value=0, max_value=100)


class RiskRequestSerializer(serializers.Serializer):
    aqi = serializers.FloatField(min_value=0)
    noise_db = serializers.FloatField(min_value=0)
    traffic = serializers.FloatField(min_value=0, max_value=100)
    weather = serializers.FloatField(min_value=0, max_value=100)
