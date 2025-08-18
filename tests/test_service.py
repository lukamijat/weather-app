import pytest
from weather.service import get_weather

def test_weather_mock(requests_mock):
    city = "London"
    api_key = "dummy"
    mock_response = {"main": {"temp": 20}, "weather": [{"description": "clear sky"}]}
    requests_mock.get(f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric",
                      json=mock_response)

    result = get_weather(city, api_key)
    assert result["main"]["temp"] == 20
    assert result["weather"][0]["description"] == "clear sky"

