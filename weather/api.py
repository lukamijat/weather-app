from flask import Flask, jsonify, request
from flask_cors import CORS
from service import get_nws_forecast_by_latlon, geocode_city

app = Flask(__name__)
CORS(app)

@app.route('/api/weather')
def weather_api():
    lat_str = request.args.get('lat')
    lon_str = request.args.get('lon')
    city = request.args.get('city')
    
    # Wenn lat ODER lon fehlt (nicht beide)
    if (lat_str and not lon_str) or (lon_str and not lat_str):
        return jsonify({"error": "Provide both lat and lon"}), 400
    
    if lat_str and lon_str:
        try:
            lat = float(lat_str)
            lon = float(lon_str)
            forecast = get_nws_forecast_by_latlon(lat, lon)
            return jsonify(forecast)  # ✅ Immer return
        except ValueError:
            return jsonify({"error": "Invalid lat/lon format"}), 400
            
    elif city:
        try:
            lat, lon = geocode_city(city)
            forecast = get_nws_forecast_by_latlon(lat, lon)
            return jsonify(forecast)  # ✅ Immer return
        except Exception as e:
            return jsonify({"error": f"Geocoding failed: {e}"}), 400
            
    else:
        return jsonify({"error": "Provide either lat/lon or city"}), 400  # ✅ Immer return
    
if __name__ == '__main__':
    print("🚀 Starting Flask server...")
    app.run(debug=True, host='0.0.0.0', port=5000)  # host='0.0.0.0' für externen Zugriff