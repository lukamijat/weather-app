import os
import argparse
from weather.service import get_weather

def main():
    parser = argparse.ArgumentParser(description="Weather CLI App")
    parser.add_argument("city", help="City name")
    args = parser.parse_args()

    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        raise RuntimeError("Please set the OPENWEATHER_API_KEY environment variable.")

    weather = get_weather(args.city, api_key)
    print(f"Weather in {args.city}: {weather['main']['temp']}°C, {weather['weather'][0]['description']}")
    
if __name__ == "__main__":
    main()
