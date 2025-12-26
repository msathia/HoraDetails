from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from datetime import datetime
from typing import Optional
import time
import re
import os

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

# Common geoname IDs
LOCATIONS = {
    "austin": 4671654,
    "san_diego": 5391811,
    "los_angeles": 5368361,
    "new_york": 5128581,
    "chicago": 4887398,
    "houston": 4699066,
    "san_francisco": 5391959,
    "chennai": 1264527,
    "hyderabad": 1269843,
    "mumbai": 1275339,
    "bangalore": 1277333,
    "delhi": 1273294,
    "kolkata": 1275004,
    "london": 2643743,
    "sydney": 2147714,
    "singapore": 1880252,
}


def get_chrome_driver():
    """Configure and return Chrome WebDriver for headless operation."""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    # For Cloud Run, Chrome is installed at a specific path
    if os.path.exists("/usr/bin/chromium"):
        chrome_options.binary_location = "/usr/bin/chromium"
    elif os.path.exists("/usr/bin/chromium-browser"):
        chrome_options.binary_location = "/usr/bin/chromium-browser"
    elif os.path.exists("/usr/bin/google-chrome"):
        chrome_options.binary_location = "/usr/bin/google-chrome"
    
    return webdriver.Chrome(options=chrome_options)


def time_to_minutes(time_str: str, ampm: str) -> int:
    """Convert time string to minutes since midnight."""
    parts = time_str.split(':')
    hour, minute = int(parts[0]), int(parts[1])
    if ampm == 'PM' and hour != 12:
        hour += 12
    elif ampm == 'AM' and hour == 12:
        hour = 0
    return hour * 60 + minute


def scrape_hora(geoname_id: int, date_str: str) -> dict:
    """Scrape hora data from Drik Panchang."""
    url = f"https://www.drikpanchang.com/muhurat/hora.html?geoname-id={geoname_id}&date={date_str}"
    
    driver = get_chrome_driver()
    
    try:
        driver.get(url)
        time.sleep(6)
        
        page_title = driver.title
        page_source = driver.page_source
        
        # Extract running hora
        running_hora_match = re.search(
            r'Running Hora.*?<div class="dpPHeaderLeftTitle">(.*?)</div>.*?(\d{1,2}:\d{2})\s*<span[^>]*>([AP]M)</span>\s*<span[^>]*>to\s*</span>.*?(\d{1,2}:\d{2})\s*<span[^>]*>([AP]M)</span>',
            page_source, re.DOTALL
        )
        
        # Extract all hora entries
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
        
        # Current time analysis
        now = datetime.now()
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
        
        return {
            'success': True,
            'title': page_title,
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


@app.get("/locations")
async def get_locations():
    """Get list of available preset locations with their geoname IDs."""
    return {
        "locations": {k: {"geoname_id": v, "name": k.replace("_", " ").title()} 
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
    # Determine geoname_id
    if location:
        location_key = location.lower().replace(" ", "_")
        if location_key not in LOCATIONS:
            raise HTTPException(
                status_code=400, 
                detail=f"Unknown location '{location}'. Use /locations to see available options."
            )
        geo_id = LOCATIONS[location_key]
    elif geoname_id:
        geo_id = geoname_id
    else:
        # Default to Austin, TX
        geo_id = LOCATIONS["austin"]
    
    # Determine date
    if date:
        date_str = date
    else:
        date_str = datetime.now().strftime("%d/%m/%Y")
    
    # Scrape hora data
    result = scrape_hora(geo_id, date_str)
    
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
    
    return {
        "current_time": result["current_time"],
        "current_hora": result["current_hora"],
        "next_hora": result["next_hora"],
        "recommendation": get_recommendation(result["current_hora"]),
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


def get_recommendation(hora: dict) -> str:
    """Get recommendation text based on current hora."""
    if not hora:
        return "Unable to determine current hora"
    
    planet = hora.get('planet', '')
    quality = hora.get('quality', 'neutral')
    
    if quality == 'good':
        return f"✅ GOOD TIME - {planet} Hora is favorable for important activities"
    elif quality == 'avoid':
        return f"⚠️ CAUTION - {planet} Hora - Avoid starting new important tasks"
    else:
        return f"🔸 NEUTRAL - {planet} Hora - Good for authority/government matters"


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)

