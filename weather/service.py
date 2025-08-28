from typing import Any, Dict, Optional, Tuple
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)
BASE = "https://api.weather.gov"

def _build_session(retries: int = 3, backoff_factor: float = 0.5) -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
    )
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers.update({
        "User-Agent": "weather-cli/0.1 (luka.mijatovic@fielmann.com)",
        "Accept": "application/ld+json, application/json"
    })
    return s

def geocode_city(city: str, session: Optional[requests.Session] = None, timeout: float = 5.0) -> Tuple[float, float]:
    if not city or not city.strip():
        raise ValueError("city must be provided for geocoding")
    
    if session is None:
        session = _build_session()
        
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": city, "format": "json", "limit": 1, "addressdetails": 0}
    resp = session.get(url, params=params, timeout=timeout)
    resp.raise_for_status()
    hits = resp.json()
    
    if not hits:
        raise ValueError("No geocoding result for {city!r}")
    
    try:
        lat = float(hits[0]["lat"])
        lon = float(hits[0]["lon"])
    except (KeyError, TypeError, ValueError) as exc:
        raise requests.exceptions.RequestException("Malformed geocode response") from exc
    
    return lat, lon

class ForecastNotFoundError(requests.exceptions.RequestException):
    """Raised when the NWS /points response contains no forecast URLs for a point."""
    pass

def get_nws_forecast_by_latlon(
    lat: float,
    lon: float,
    session: Optional[requests.Session] = None,
    timeout: float = 5.0,
    hourly: bool = False,
) -> Dict[str, Any]:
    if session is None:
        session = _build_session()
        
    points_url = f"{BASE}/points/{lat},{lon}"
    logger.debug("Requesting points URL %s", points_url)

    r = session.get(points_url, timeout=timeout)
    
    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError:
        # log response body for debugging before re-raising
        try:
            logger.debug("Points error response JSON: %s", r.json())
        except Exception:
            logger.debug("Points error response text: %s", r.text)
        raise

    # Now safely parse JSON (we know it's a 2xx)
    try:
        points = r.json()
    except ValueError:
        logger.debug("Points response was not JSON; text: %s", r.text)
        points = {}

    # debug: if logger is DEBUG, print full points dict so user can see exact API response
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Full /points response: %s", points)

    props = points.get("properties") if isinstance(points.get("properties"), dict) else points or {}
    logger.debug("Points properties keys: %s", list(props.keys()))

    
    if not props:
        raise ForecastNotFoundError(
            f"No 'properties' in points response for {lat},{lon} (likely outside NWS coverage)."
        )

    
    candidates = []
    if hourly:
        candidates.extend([props.get("forecastHourly"), props.get("forecast")])
    else:
        candidates.extend([props.get("forecast"), props.get("forecastHourly")])
    if props.get("forecastGridData"):
        candidates.append(props.get("forecastGridData"))

    
    uniq = []
    seen = set()
    for c in candidates:
        if c and c not in seen:
            uniq.append(c)
            seen.add(c)
    candidates = uniq

    if not candidates:
        raise ForecastNotFoundError(
            f"No forecast endpoints found for {lat},{lon}; available properties: {', '.join(sorted(props.keys()))}"
        )

    last_exc: Optional[Exception] = None
    for url in candidates:
        logger.debug("Trying forecast URL: %s", url)
        try:
            r2 = session.get(url, timeout=timeout)
            r2.raise_for_status()
            forecast = r2.json()
            periods = (forecast.get("properties", {}) or {}).get("periods") or forecast.get("periods")
            if periods:
                current = periods[0]
                return {
                    "name": current.get("name"),
                    "startTime": current.get("startTime"),
                    "temperature": current.get("temperature"),
                    "unit": current.get("temperatureUnit"),
                    "short": current.get("shortForecast"),
                    "detailed": current.get("detailedForecast"),
                    "source_json": forecast,
                }
            
            return {
                "temperature": None,
                "unit": None,
                "short": None,
                "detailed": None,
                "source_json": forecast,
            }
        except requests.exceptions.HTTPError as e:
            logger.debug("Forecast URL returned HTTP error %s, trying next candidate", e)
            last_exc = e
            continue
        except requests.exceptions.RequestException as e:
            logger.debug("Network error when calling forecast URL %s: %s", url, e)
            last_exc = e
            continue

   
    raise requests.exceptions.RequestException("All forecast endpoints failed for this point.") from last_exc
