import pytest
import requests
from weather import service


@pytest.mark.skipif(not hasattr(service, "get_weather"), reason="get_weather not implemented")
def test_get_weather_monkeypatch(monkeypatch):
    """
    Legacy OpenWeather-style test: monkeypatch _build_session to return a DummySession
    so no real HTTP calls are made. This verifies params and that JSON is returned.
    """
    city = "Seattle"
    api_key = "dummy"
    mock_response = {"main": {"temp": 20}, "weather": [{"description": "clear sky"}]}

    class DummyResp:
        def __init__(self, json_data, status_code=200):
            self._json = json_data
            self.status_code = status_code

        def raise_for_status(self):
            if 400 <= self.status_code:
                raise requests.exceptions.HTTPError("HTTP error")

        def json(self):
            return self._json

    class DummySession:
        def mount(self, *a, **k):
            pass

        def get(self, url, params=None, timeout=None):
            
            assert params is not None
            assert params.get("q") == city
            assert params.get("appid") == api_key
            assert "units" in params
            return DummyResp(mock_response)

    monkeypatch.setattr(service, "_build_session", lambda *a, **k: DummySession())
    result = service.get_weather(city, api_key)
    assert result["main"]["temp"] == 20
    assert result["weather"][0]["description"] == "clear sky"


@pytest.mark.skipif(not hasattr(service, "get_nws_forecast_by_latlon"), reason="NWS function not implemented")
def test_get_nws_forecast_by_latlon_success():
    """
    Test the NWS flow: first call to /points returns a forecast URL, second call
    to that forecast URL returns a forecast JSON with properties.periods.
    """
    lat = 38.9072
    lon = -77.0369

    points_json = {
        "properties": {
            "forecast": "https://api.weather.gov/fake/forecast"
        }
    }

    forecast_json = {
        "properties": {
            "periods": [
                {
                    "number": 1,
                    "name": "Now",
                    "startTime": "2025-08-25T10:00:00-04:00",
                    "temperature": 75,
                    "temperatureUnit": "F",
                    "shortForecast": "Partly Sunny",
                    "detailedForecast": "Partly sunny, with a gentle breeze."
                }
            ]
        }
    }

    class DummySession:
        def __init__(self):
            self.calls = []

        def get(self, url, params=None, timeout=None):
            self.calls.append(url)
            if "/points/" in url:
                class R:
                    def raise_for_status(self_inner): pass
                    def json(self_inner): return points_json
                return R()
            elif "fake/forecast" in url:
                class R:
                    def raise_for_status(self_inner): pass
                    def json(self_inner): return forecast_json
                return R()
            else:
                raise requests.exceptions.RequestException("Unexpected URL: " + url)

    sess = DummySession()
    result = service.get_nws_forecast_by_latlon(lat, lon, session=sess)
    assert result["temperature"] == 75
    assert result["unit"] == "F"
    assert "Partly Sunny" in result["short"]


@pytest.mark.skipif(not hasattr(service, "get_nws_forecast_by_latlon"), reason="NWS function not implemented")
def test_get_nws_forecast_by_latlon_no_forecast_url_raises():
    """
    If the /points response does not contain any forecast URLs, the service
    should raise a requests.exceptions.RequestException indicating no forecast URL.
    """
    lat = 0.0
    lon = 0.0

    points_json = {"properties": {"relativeLocation": {"properties": {"name": "Ocean"}}}}

    class DummySession:
        def get(self, url, params=None, timeout=None):
            class R:
                def raise_for_status(self_inner): pass
                def json(self_inner): return points_json
            return R()

    with pytest.raises(requests.exceptions.RequestException) as excinfo:
        service.get_nws_forecast_by_latlon(lat, lon, session=DummySession())

    assert "forecast URL not found" in str(excinfo.value) or "available properties" in str(excinfo.value)

def test_geocode_city_success():
    city = "Seattle"
    fake_resp = [{"lat": "47.6062", "lon": "-122.3321"}]
    
    class DummySession:
        def get(self, url, params=None, timeout=None):
            assert "nominatim.openstreetmap.org" in url
            assert params and params.get("q") == city
            class R:
                def raise_for_status(self): pass
                def json(self): return fake_resp
            return R()
        
    lat, lon = service.geocode_city(city, session=DummySession())
    assert pytest.approx(lat, rel=1e-4) == 47.6062
    assert pytest.approx(lon, rel=1e-4) == -122.3321
    
def test_geocode_city_no_result():
    class DummySession:
        def get(self, url, params=None, timeout=None):
            class R:
                def raise_for_status(self): pass
                def json(self): return []
            return R()
    with pytest.raises(ValueError):
        service.geocode_city("no-such-place-xyz", session=DummySession())    
            