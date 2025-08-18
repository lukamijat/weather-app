import requests

def get_weather(city: str, api_key: str) -> dict:
    """Fetch current weather for a given city using OpenWeather API."""
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    response = requests.get(url, timeout=5)
    response.raise_for_status()
    return response.json()
