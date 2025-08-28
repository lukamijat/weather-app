import os
import sys
import argparse
import logging
from typing import Sequence, Optional, Tuple

from . import service
import requests

logger = logging.getLogger(__name__)


def format_pretty_nws(lat: float, lon: float, payload: dict) -> str:
    temp = payload.get("temperature")
    unit = payload.get("unit") or ""
    short = payload.get("short") or payload.get("detailed")
    
    if not short:
        src = payload.get("source_json", {})
        p0 = (src.get("properties", {}) or {}).get("periods") or src.get("periods") or []
        if p0:
            short = p0[0].get("shortForecast") or p0[0].get("detailedForecast")
    
    if temp is None:
        short = short or "No forecast available"
        return f"Weather at {lat},{lon}: {short}"
    else:
        unit_display = f"°{unit}" if unit else ""
        short = short or "No forecast available"
        return f"Weather at {lat},{lon}: {temp}{unit_display} - {short}"
    

def _resolve_latlon_from_city(city: str, timeout: float = 5.0) -> tuple[float, float]:
    geocode = getattr(service, "geocode_city", None)
    if not callable(geocode):
        raise ValueError("Geocoding is not available. Please provide --lat and --lon.")
    return geocode(city, timeout=timeout)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Weather CLI App (National Weather Service of the United States of America)")
    parser.add_argument("city", nargs="?", help="City name (e.g. 'New York City' or 'Seattle'). Optional if --lat/--lon provided.")
    parser.add_argument("--lat",  type=float, help="Latitude Lookup for NWS (overrides city)")
    parser.add_argument("--lon", type=float, help="Longitude Lookup for NWS (overrides city)")
    parser.add_argument("--hourly", action="store_true", help="Request hourly forecast instead of period forecast")
    parser.add_argument("--timeout", type=float, default=5.0, help="Request timeout in seconds")
    parser.add_argument("--json", action="store_true", help="Print raw JSON (source forecast) instead of pretty text")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args(argv)
    
    if args.debug:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
    else:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    
    lat: Optional[float] = args.lat
    lon: Optional[float] = args.lon
    
    if lat is None or lon is None:
        if args.city:
            try:
                lat, lon = _resolve_latlon_from_city(args.city, timeout=args.timeout)
            except ValueError as e:
                logger.error(str(e))
                return 2
            except requests.exceptions.RequestException as e:
                logger.error("Network/Geocoding error: %s", e)
                return 4
            except Exception:
                logger.exception("Unexpected error during geocoding")
                return 5
        else:
            logger.error("Either provide a city name or both --lat and --lon")
            return 2
        
    try:
        payload = service.get_nws_forecast_by_latlon(lat, lon, timeout=args.timeout, hourly=args.hourly)
    except getattr(service, "ForecastNotFoundError", Exception) as e:
        logger.error("No forecast available for that location: %s", e)
        return 2
    except requests.exceptions.HTTPError as e:
        logger.error("HTTP error when fetching forecast: %s", e)
        return 3
    except requests.exceptions.RequestException as e:
        logger.error("Network error when fetching forecast: %s", e)
        return 4
    except Exception:
        logger.exception("Unexpected error when fetching forecast")
        return 5
    
    if args.json:
        import json
        to_print = payload.get("source_json", payload)
        print(json.dumps(to_print, indent=2), flush=True)
    else:
        print(format_pretty_nws(lat, lon, payload), flush=True)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())