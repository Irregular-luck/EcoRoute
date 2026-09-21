from unittest import TestCase
from .risk import calculate_risk


class RiskEngineTests(TestCase):
    def test_low_exposure_is_safe(self):
        result = calculate_risk(aqi=30, noise_db=52, traffic=15, weather=10)
        self.assertLessEqual(result.total, 30)
        self.assertEqual(result.category, "Safe")

    def test_high_exposure_is_high_risk(self):
        result = calculate_risk(aqi=210, noise_db=90, traffic=90, weather=80)
        self.assertGreater(result.total, 60)
        self.assertEqual(result.category, "High Risk")
