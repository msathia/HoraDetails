from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional
import time
import re
import os

# Simple cache for scraped data (cache for 5 minutes)
_hora_cache = {}
CACHE_DURATION_MINUTES = 5

app = FastAPI(
    title="Hora API",
    description="🕉️ Vedic Planetary Hours (Hora) API - Get auspicious timings from Drik Panchang",
    version="1.0.0",
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Planet metadata
PLANET_INFO = {
    "Sun": {"emoji": "☀️", "nature": "Vigorous", "quality": "neutral"},
    "Moon": {"emoji": "🌙", "nature": "Gentle", "quality": "good"},
    "Mars": {"emoji": "♂️", "nature": "Aggressive", "quality": "avoid"},
    "Mercury": {"emoji": "☿", "nature": "Quick", "quality": "good"},
    "Jupiter": {"emoji": "♃", "nature": "Fruitful", "quality": "good"},
    "Venus": {"emoji": "♀️", "nature": "Beneficial", "quality": "good"},
    "Saturn": {"emoji": "♄", "nature": "Sluggish", "quality": "avoid"},
}

# Common geoname IDs with timezone and coordinates
LOCATIONS = {
    "austin": {"geoname_id": 4671654, "timezone": "America/Chicago", "lat": 30.2672, "lng": -97.7431},
    "san_diego": {"geoname_id": 5391811, "timezone": "America/Los_Angeles", "lat": 32.7157, "lng": -117.1611},
    "los_angeles": {"geoname_id": 5368361, "timezone": "America/Los_Angeles", "lat": 34.0522, "lng": -118.2437},
    "new_york": {"geoname_id": 5128581, "timezone": "America/New_York", "lat": 40.7128, "lng": -74.0060},
    "chicago": {"geoname_id": 4887398, "timezone": "America/Chicago", "lat": 41.8781, "lng": -87.6298},
    "houston": {"geoname_id": 4699066, "timezone": "America/Chicago", "lat": 29.7604, "lng": -95.3698},
    "san_francisco": {"geoname_id": 5391959, "timezone": "America/Los_Angeles", "lat": 37.7749, "lng": -122.4194},
    "chennai": {"geoname_id": 1264527, "timezone": "Asia/Kolkata", "lat": 13.0827, "lng": 80.2707},
    "hyderabad": {"geoname_id": 1269843, "timezone": "Asia/Kolkata", "lat": 17.3850, "lng": 78.4867},
    "mumbai": {"geoname_id": 1275339, "timezone": "Asia/Kolkata", "lat": 19.0760, "lng": 72.8777},
    "bangalore": {"geoname_id": 1277333, "timezone": "Asia/Kolkata", "lat": 12.9716, "lng": 77.5946},
    "delhi": {"geoname_id": 1273294, "timezone": "Asia/Kolkata", "lat": 28.6139, "lng": 77.2090},
    "kolkata": {"geoname_id": 1275004, "timezone": "Asia/Kolkata", "lat": 22.5726, "lng": 88.3639},
    "london": {"geoname_id": 2643743, "timezone": "Europe/London", "lat": 51.5074, "lng": -0.1278},
    "sydney": {"geoname_id": 2147714, "timezone": "Australia/Sydney", "lat": -33.8688, "lng": 151.2093},
    "singapore": {"geoname_id": 1880252, "timezone": "Asia/Singapore", "lat": 1.3521, "lng": 103.8198},
}


def get_chrome_driver(timezone: str = "America/Chicago", latitude: float = 30.2672, longitude: float = -97.7431):
    """Configure and return Chrome WebDriver for headless operation with location emulation."""
    # Set timezone environment variable to match target location
    os.environ['TZ'] = timezone
    
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    # Allow geolocation so we can spoof it
    prefs = {
        "profile.default_content_setting_values.geolocation": 1,  # Allow geolocation
        "profile.default_content_setting_values.notifications": 2,  # Block notifications
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    # For Cloud Run, Chrome is installed at a specific path
    if os.path.exists("/usr/bin/chromium"):
        chrome_options.binary_location = "/usr/bin/chromium"
    elif os.path.exists("/usr/bin/chromium-browser"):
        chrome_options.binary_location = "/usr/bin/chromium-browser"
    elif os.path.exists("/usr/bin/google-chrome"):
        chrome_options.binary_location = "/usr/bin/google-chrome"
    
    driver = webdriver.Chrome(options=chrome_options)
    
    # Emulate Austin, TX location using Chrome DevTools Protocol
    try:
        # Set timezone
        driver.execute_cdp_cmd('Emulation.setTimezoneOverride', {'timezoneId': timezone})
        
        # Set geolocation to Austin, TX coordinates
        driver.execute_cdp_cmd('Emulation.setGeolocationOverride', {
            'latitude': latitude,
            'longitude': longitude,
            'accuracy': 100
        })
    except Exception:
        pass  # CDP commands may not be supported in all Chrome versions
    
    return driver


def time_to_minutes(time_str: str, ampm: str) -> int:
    """Convert time string to minutes since midnight."""
    parts = time_str.split(':')
    hour, minute = int(parts[0]), int(parts[1])
    if ampm == 'PM' and hour != 12:
        hour += 12
    elif ampm == 'AM' and hour == 12:
        hour = 0
    return hour * 60 + minute


def scrape_hora(geoname_id: int, date_str: str, timezone_str: str = "America/Chicago", lat: float = 30.2672, lng: float = -97.7431) -> dict:
    """Scrape hora data from Drik Panchang using explicit geoname-id with location emulation."""
    global _hora_cache
    
    # Create cache key
    cache_key = f"{geoname_id}_{date_str}"
    
    # Check if we have valid cached data
    if cache_key in _hora_cache:
        cached_data, cached_time = _hora_cache[cache_key]
        if datetime.now() - cached_time < timedelta(minutes=CACHE_DURATION_MINUTES):
            # Update current_time in cached data to reflect actual current time
            tz = ZoneInfo(timezone_str)
            now = datetime.now(tz)
            cached_data['current_time'] = now.strftime("%I:%M %p")
            
            # Re-calculate current hora based on actual current time
            current_minutes = now.hour * 60 + now.minute
            for i, hora in enumerate(cached_data.get('full_schedule', [])):
                start_mins = hora['start_minutes']
                end_mins = hora['end_minutes']
                if end_mins < start_mins:
                    end_mins += 24 * 60
                    check_mins = current_minutes + 24 * 60 if current_minutes < 12 * 60 else current_minutes
                else:
                    check_mins = current_minutes
                if start_mins <= check_mins < end_mins:
                    cached_data['current_hora'] = hora
                    if i + 1 < len(cached_data['full_schedule']):
                        cached_data['next_hora'] = cached_data['full_schedule'][i + 1]
                    break
            
            return cached_data
    
    # Use geoname-id parameter - this determines the location's hora schedule
    # geoname-id=4671654 for Austin, TX
    url = f"https://www.drikpanchang.com/muhurat/hora.html?geoname-id={geoname_id}&date={date_str}"
    
    driver = get_chrome_driver(timezone_str, lat, lng)
    
    try:
        # Try up to 3 times to get valid Austin data
        valid_data = False
        for attempt in range(3):
            driver.get(url)
            time.sleep(6 + attempt * 2)  # Wait longer on retries
            
            page_source = driver.page_source
            
            # For Austin, validate first hora starts around 7:20-7:30 AM
            if geoname_id == 4671654:
                first_match = re.search(r'(\d{1,2}):(\d{2})\s*<span[^>]*>AM</span>', page_source)
                if first_match:
                    hour = int(first_match.group(1))
                    minute = int(first_match.group(2))
                    first_minutes = hour * 60 + minute
                    # Austin sunrise in Dec is ~7:20-7:30 AM (440-450 minutes)
                    if 435 <= first_minutes <= 455:
                        valid_data = True
                        break
                    # Wrong data, clear cookies and retry
                    driver.delete_all_cookies()
            else:
                valid_data = True
                break
        
        if not valid_data and geoname_id == 4671654:
            # Last attempt, just accept whatever we get
            driver.get(url)
            time.sleep(8)
            page_source = driver.page_source
        
        page_title = driver.title
        page_source = driver.page_source
        
        # Extract location from page title
        location_match = re.search(r'for\s+([^,]+,\s*[^,]+,\s*[^"<]+)', page_title)
        detected_location = location_match.group(1).strip() if location_match else "Unknown"
        
        # Extract running hora
        running_hora_match = re.search(
            r'Running Hora.*?<div class="dpPHeaderLeftTitle">(.*?)</div>.*?(\d{1,2}:\d{2})\s*<span[^>]*>([AP]M)</span>\s*<span[^>]*>to\s*</span>.*?(\d{1,2}:\d{2})\s*<span[^>]*>([AP]M)</span>',
            page_source, re.DOTALL
        )
        
        # Extract all hora entries from the table
        hora_pattern = r'<span class="dpVerticalMiddleText">(Jupiter|Mars|Sun|Venus|Mercury|Moon|Saturn)\s*-\s*(Fruitful|Aggressive|Vigorous|Beneficial|Quick|Gentle|Sluggish).*?</span>.*?<span class="dpVerticalMiddleText">(\d{1,2}:\d{2})\s*<span[^>]*>([AP]M)</span>\s*<span[^>]*>to\s*</span>.*?(\d{1,2}:\d{2})\s*<span[^>]*>([AP]M)</span>'
        matches = re.findall(hora_pattern, page_source, re.DOTALL)
        
        # Build hora schedule
        hora_schedule = []
        for planet, nature, start_time, start_ampm, end_time, end_ampm in matches:
            hora_schedule.append({
                'planet': planet,
                'nature': nature,
                'emoji': PLANET_INFO.get(planet, {}).get('emoji', '🌟'),
                'quality': PLANET_INFO.get(planet, {}).get('quality', 'neutral'),
                'start': f"{start_time} {start_ampm}",
                'end': f"{end_time} {end_ampm}",
                'start_minutes': time_to_minutes(start_time, start_ampm),
                'end_minutes': time_to_minutes(end_time, end_ampm),
            })
        
        # Current time analysis - USE LOCATION'S TIMEZONE
        tz = ZoneInfo(timezone_str)
        now = datetime.now(tz)
        current_minutes = now.hour * 60 + now.minute
        
        current_hora = None
        next_hora = None
        
        for i, hora in enumerate(hora_schedule):
            start_mins = hora['start_minutes']
            end_mins = hora['end_minutes']
            
            # Handle overnight
            if end_mins < start_mins:
                end_mins += 24 * 60
                check_mins = current_minutes + 24 * 60 if current_minutes < 12 * 60 else current_minutes
            else:
                check_mins = current_minutes
            
            if start_mins <= check_mins < end_mins:
                current_hora = hora
                if i + 1 < len(hora_schedule):
                    next_hora = hora_schedule[i + 1]
                break
        
        # Extract from running hora if available
        if running_hora_match and not current_hora:
            planet_nature = running_hora_match.group(1)
            planet = planet_nature.split(' - ')[0].strip()
            nature = planet_nature.split(' - ')[1].strip() if ' - ' in planet_nature else ""
            current_hora = {
                'planet': planet,
                'nature': nature,
                'emoji': PLANET_INFO.get(planet, {}).get('emoji', '🌟'),
                'quality': PLANET_INFO.get(planet, {}).get('quality', 'neutral'),
                'start': f"{running_hora_match.group(2)} {running_hora_match.group(3)}",
                'end': f"{running_hora_match.group(4)} {running_hora_match.group(5)}",
            }
        
        # Separate day and night horas
        day_horas = hora_schedule[:12] if len(hora_schedule) >= 12 else hora_schedule
        night_horas = hora_schedule[12:24] if len(hora_schedule) >= 24 else hora_schedule[12:]
        
        # Get Jupiter horas
        jupiter_horas = [h for h in hora_schedule if h['planet'] == 'Jupiter']
        
        result = {
            'success': True,
            'title': page_title,
            'location': detected_location,
            'date': date_str,
            'geoname_id': geoname_id,
            'current_time': now.strftime("%I:%M %p"),
            'current_hora': current_hora,
            'next_hora': next_hora,
            'jupiter_horas': jupiter_horas,
            'day_horas': day_horas,
            'night_horas': night_horas,
            'full_schedule': hora_schedule,
        }
        
        # Cache the result
        _hora_cache[cache_key] = (result.copy(), datetime.now())
        
        return result
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
        }
    finally:
        driver.quit()


@app.get("/")
async def root():
    """API root - welcome message and available endpoints."""
    return {
        "message": "🕉️ Hora API - Vedic Planetary Hours",
        "version": "1.0.0",
        "endpoints": {
            "/hora": "Get hora schedule for a location",
            "/locations": "List available preset locations",
            "/health": "Health check endpoint",
            "/docs": "Interactive API documentation",
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/ip")
async def get_server_ip():
    """Check the server's outbound IP address and location."""
    import urllib.request
    import json as json_lib
    try:
        with urllib.request.urlopen('https://ipinfo.io/json', timeout=5) as response:
            data = json_lib.loads(response.read().decode())
            return {
                "ip": data.get("ip"),
                "city": data.get("city"),
                "region": data.get("region"),
                "country": data.get("country"),
                "org": data.get("org"),
                "timezone": data.get("timezone"),
            }
    except Exception as e:
        return {"error": str(e)}


@app.get("/locations")
async def get_locations():
    """Get list of available preset locations with their geoname IDs."""
    return {
        "locations": {k: {"geoname_id": v["geoname_id"], "timezone": v["timezone"], "name": k.replace("_", " ").title()} 
                      for k, v in LOCATIONS.items()}
    }


@app.get("/hora")
async def get_hora(
    location: Optional[str] = Query(None, description="Preset location name (e.g., 'austin', 'chennai')"),
    geoname_id: Optional[int] = Query(None, description="Custom geoname ID from drikpanchang.com"),
    date: Optional[str] = Query(None, description="Date in DD/MM/YYYY format (defaults to today)")
):
    """
    Get Hora (planetary hour) schedule for a location.
    
    Either provide a preset `location` name or a custom `geoname_id`.
    
    **Examples:**
    - `/hora?location=austin` - Austin, TX
    - `/hora?location=chennai` - Chennai, India
    - `/hora?geoname_id=1264527` - Custom location
    - `/hora?location=austin&date=25/12/2025` - Specific date
    """
    # Determine geoname_id, timezone, and coordinates
    if location:
        location_key = location.lower().replace(" ", "_")
        if location_key not in LOCATIONS:
            raise HTTPException(
                status_code=400, 
                detail=f"Unknown location '{location}'. Use /locations to see available options."
            )
        loc_info = LOCATIONS[location_key]
        geo_id = loc_info["geoname_id"]
        timezone_str = loc_info["timezone"]
        lat = loc_info["lat"]
        lng = loc_info["lng"]
    elif geoname_id:
        geo_id = geoname_id
        # Default to Austin for custom geoname_id
        timezone_str = "America/Chicago"
        lat = 30.2672
        lng = -97.7431
    else:
        # Default to Austin, TX
        loc_info = LOCATIONS["austin"]
        geo_id = loc_info["geoname_id"]
        timezone_str = loc_info["timezone"]
        lat = loc_info["lat"]
        lng = loc_info["lng"]
    
    # Determine date - USE LOCATION'S TIMEZONE for today's date
    if date:
        date_str = date
    else:
        tz = ZoneInfo(timezone_str)
        local_now = datetime.now(tz)
        date_str = local_now.strftime("%d/%m/%Y")
    
    # Scrape hora data with location emulation
    result = scrape_hora(geo_id, date_str, timezone_str, lat, lng)
    
    if not result['success']:
        raise HTTPException(status_code=500, detail=result.get('error', 'Failed to fetch hora data'))
    
    return result


@app.get("/hora/current")
async def get_current_hora(
    location: Optional[str] = Query("austin", description="Preset location name"),
    geoname_id: Optional[int] = Query(None, description="Custom geoname ID")
):
    """Get only the current running hora (lightweight response)."""
    result = await get_hora(location=location, geoname_id=geoname_id)
    
    # Find next Jupiter hora
    next_jupiter = find_next_jupiter_hora(result.get("full_schedule", []), result.get("current_hora"))
    
    return {
        "location": result.get("location", "Unknown"),
        "current_time": result["current_time"],
        "current_hora": result["current_hora"],
        "next_hora": result["next_hora"],
        "next_jupiter_hora": next_jupiter,
        "recommendation": get_recommendation(result["current_hora"], next_jupiter),
    }


@app.get("/hora/jupiter")
async def get_jupiter_horas(
    location: Optional[str] = Query("austin", description="Preset location name"),
    geoname_id: Optional[int] = Query(None, description="Custom geoname ID"),
    date: Optional[str] = Query(None, description="Date in DD/MM/YYYY format")
):
    """Get only Jupiter (most auspicious) hora times for the day."""
    result = await get_hora(location=location, geoname_id=geoname_id, date=date)
    
    return {
        "date": result["date"],
        "jupiter_horas": result["jupiter_horas"],
        "best_for": [
            "Starting new ventures & businesses",
            "Education & learning",
            "Legal matters & signing contracts",
            "Spiritual activities & prayers",
        ]
    }


def find_next_jupiter_hora(full_schedule: list, current_hora: dict) -> dict:
    """Find the next upcoming Jupiter hora after the current hora."""
    if not full_schedule or not current_hora:
        return None
    
    current_start = current_hora.get('start_minutes', 0)
    
    # Find Jupiter horas that start after current hora
    for hora in full_schedule:
        if hora['planet'] == 'Jupiter':
            hora_start = hora.get('start_minutes', 0)
            # Handle overnight (if Jupiter hora is early morning and current is evening)
            if hora_start > current_start or (current_start > 1200 and hora_start < 400):
                return hora
    
    # If no future Jupiter hora found, return the first one (next day)
    for hora in full_schedule:
        if hora['planet'] == 'Jupiter':
            return hora
    
    return None


def get_recommendation(hora: dict, next_jupiter: dict = None) -> str:
    """Get recommendation text based on current hora."""
    if not hora:
        return "Unable to determine current hora"
    
    planet = hora.get('planet', '')
    quality = hora.get('quality', 'neutral')
    
    # Base recommendation
    if quality == 'good':
        recommendation = f"✅ GOOD TIME - {planet} Hora is favorable for important activities"
    elif quality == 'avoid':
        recommendation = f"⚠️ CAUTION - {planet} Hora - Avoid starting new important tasks"
    else:
        recommendation = f"🔸 NEUTRAL - {planet} Hora - Good for authority/government matters"
    
    # Add next Jupiter hora info if current is not Jupiter
    if planet != 'Jupiter' and next_jupiter:
        jupiter_start = next_jupiter.get('start', '')
        recommendation += f" | ♃ Next Jupiter Hora: {jupiter_start}"
    
    return recommendation


def generate_hora_html(data: dict) -> str:
    """Generate beautiful HTML page for hora data."""
    location = data.get('location', 'Unknown')
    current_time = data.get('current_time', '')
    date = data.get('date', '')
    current_hora = data.get('current_hora', {})
    next_hora = data.get('next_hora', {})
    jupiter_horas = data.get('jupiter_horas', [])
    day_horas = data.get('day_horas', [])
    night_horas = data.get('night_horas', [])
    
    current_planet = current_hora.get('planet', 'Unknown')
    current_emoji = current_hora.get('emoji', '🌟')
    current_quality = current_hora.get('quality', 'neutral')
    current_start = current_hora.get('start', '')
    current_end = current_hora.get('end', '')
    
    # Quality styling
    quality_colors = {
        'good': ('#10b981', '#d1fae5', '✅ Auspicious'),
        'avoid': ('#ef4444', '#fee2e2', '⚠️ Avoid'),
        'neutral': ('#f59e0b', '#fef3c7', '🔸 Neutral')
    }
    q_color, q_bg, q_text = quality_colors.get(current_quality, quality_colors['neutral'])
    
    # Generate day horas table rows
    day_rows = ""
    for i, hora in enumerate(day_horas):
        quality = hora.get('quality', 'neutral')
        bg = '#d1fae5' if quality == 'good' else ('#fee2e2' if quality == 'avoid' else '#fef3c7')
        symbol = '✓' if quality == 'good' else ('✗' if quality == 'avoid' else '~')
        day_rows += f'''
        <tr style="background: {bg};">
            <td>{i+1}</td>
            <td>{hora.get('emoji', '')} {hora.get('planet', '')}</td>
            <td>{hora.get('start', '')} - {hora.get('end', '')}</td>
            <td>{hora.get('nature', '')}</td>
            <td style="font-weight: bold;">{symbol}</td>
        </tr>'''
    
    # Generate night horas table rows
    night_rows = ""
    for i, hora in enumerate(night_horas):
        quality = hora.get('quality', 'neutral')
        bg = '#d1fae5' if quality == 'good' else ('#fee2e2' if quality == 'avoid' else '#fef3c7')
        symbol = '✓' if quality == 'good' else ('✗' if quality == 'avoid' else '~')
        night_rows += f'''
        <tr style="background: {bg};">
            <td>{i+1}</td>
            <td>{hora.get('emoji', '')} {hora.get('planet', '')}</td>
            <td>{hora.get('start', '')} - {hora.get('end', '')}</td>
            <td>{hora.get('nature', '')}</td>
            <td style="font-weight: bold;">{symbol}</td>
        </tr>'''
    
    # Generate Jupiter horas list
    jupiter_list = "".join([f'<li>♃ {h.get("start", "")} - {h.get("end", "")}</li>' for h in jupiter_horas])
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🕉️ Hora - {location}</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Poppins', sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            color: #fff;
            padding: 20px;
        }}
        .container {{ max-width: 900px; margin: 0 auto; }}
        .header {{
            text-align: center;
            padding: 30px 20px;
            background: rgba(255,255,255,0.1);
            border-radius: 20px;
            margin-bottom: 25px;
            backdrop-filter: blur(10px);
        }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        .header .location {{ color: #fbbf24; font-size: 1.2em; }}
        .header .time {{ color: #94a3b8; margin-top: 10px; }}
        
        .current-hora {{
            background: {q_bg};
            color: #1a1a2e;
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 25px;
            text-align: center;
            border-left: 6px solid {q_color};
        }}
        .current-hora .planet {{ font-size: 3em; margin-bottom: 10px; }}
        .current-hora .name {{ font-size: 1.8em; font-weight: 600; color: {q_color}; }}
        .current-hora .time-range {{ font-size: 1.2em; color: #64748b; margin: 10px 0; }}
        .current-hora .quality {{ 
            display: inline-block;
            padding: 8px 20px;
            background: {q_color};
            color: white;
            border-radius: 20px;
            font-weight: 500;
        }}
        
        .jupiter-box {{
            background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
            color: #1a1a2e;
            border-radius: 20px;
            padding: 25px;
            margin-bottom: 25px;
        }}
        .jupiter-box h2 {{ margin-bottom: 15px; }}
        .jupiter-box ul {{ list-style: none; }}
        .jupiter-box li {{ 
            padding: 10px 15px;
            background: rgba(255,255,255,0.3);
            border-radius: 10px;
            margin: 8px 0;
            font-weight: 500;
        }}
        
        .schedule {{
            background: rgba(255,255,255,0.95);
            color: #1a1a2e;
            border-radius: 20px;
            padding: 25px;
            margin-bottom: 25px;
        }}
        .schedule h2 {{ 
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e2e8f0;
        }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e2e8f0; }}
        th {{ background: #1a1a2e; color: white; font-weight: 500; }}
        tr:hover {{ opacity: 0.9; }}
        
        .legend {{
            text-align: center;
            padding: 15px;
            background: rgba(255,255,255,0.1);
            border-radius: 10px;
            color: #94a3b8;
        }}
        .legend span {{ margin: 0 15px; }}
        
        .footer {{
            text-align: center;
            padding: 20px;
            color: #64748b;
            font-size: 0.9em;
        }}
        .footer a {{ color: #fbbf24; text-decoration: none; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🕉️ Hora Schedule</h1>
            <div class="location">📍 {location}</div>
            <div class="time">📅 {date} &nbsp;|&nbsp; 🕐 {current_time}</div>
        </div>
        
        <div class="current-hora">
            <div class="planet">{current_emoji}</div>
            <div class="name">{current_planet} Hora</div>
            <div class="time-range">{current_start} - {current_end}</div>
            <div class="quality">{q_text}</div>
        </div>
        
        <div class="jupiter-box">
            <h2>♃ Jupiter Hora Times (Most Auspicious)</h2>
            <ul>{jupiter_list}</ul>
        </div>
        
        <div class="schedule">
            <h2>☀️ Day Hora (Sunrise → Sunset)</h2>
            <table>
                <thead>
                    <tr><th>#</th><th>Planet</th><th>Time</th><th>Nature</th><th>Status</th></tr>
                </thead>
                <tbody>{day_rows}</tbody>
            </table>
        </div>
        
        <div class="schedule">
            <h2>🌙 Night Hora (Sunset → Sunrise)</h2>
            <table>
                <thead>
                    <tr><th>#</th><th>Planet</th><th>Time</th><th>Nature</th><th>Status</th></tr>
                </thead>
                <tbody>{night_rows}</tbody>
            </table>
        </div>
        
        <div class="legend">
            <span style="color: #10b981;">✓ Good</span>
            <span style="color: #f59e0b;">~ Neutral</span>
            <span style="color: #ef4444;">✗ Avoid</span>
        </div>
        
        <div class="footer">
            Data from <a href="https://www.drikpanchang.com" target="_blank">Drik Panchang</a> |
            <a href="/docs">API Documentation</a>
        </div>
    </div>
</body>
</html>'''
    return html


@app.get("/view", response_class=HTMLResponse)
async def view_hora(
    location: Optional[str] = Query("austin", description="Preset location name"),
    geoname_id: Optional[int] = Query(None, description="Custom geoname ID"),
    date: Optional[str] = Query(None, description="Date in DD/MM/YYYY format")
):
    """View Hora schedule as a beautiful HTML page."""
    result = await get_hora(location=location, geoname_id=geoname_id, date=date)
    return HTMLResponse(content=generate_hora_html(result))


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)

