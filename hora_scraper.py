from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from datetime import datetime
import time
import re

# ============================================================================
# LOCATION SETTINGS
# ============================================================================
# To change location: Replace the geoname_id below with your city's ID
#
# Available Geoname IDs:
#   USA:
#     - Austin, TX:      4671654 (current)
#     - San Diego, CA:   5391811
#     - Los Angeles, CA: 5368361
#     - New York, NY:    5128581
#     - Chicago, IL:     4887398
#     - Houston, TX:     4699066
#     - San Francisco:   5391959
#
#   India:
#     - Chennai:         1264527
#     - Hyderabad:       1269843
#     - Mumbai:          1275339
#     - Bangalore:       1277333
#     - Delhi:           1273294
#     - Kolkata:         1275004
#
#   Other:
#     - London, UK:      2643743
#     - Sydney, AU:      2147714
#     - Singapore:       1880252
#
# To find other cities: Visit drikpanchang.com and search for your city,
# then copy the geoname-id from the URL
# ============================================================================

geoname_id = 4671654  # Change this to your city's geoname ID

# Dynamic date - uses today's date
today = datetime.now()
date_str = today.strftime("%d/%m/%Y")  # Format: DD/MM/YYYY

# URL with geoname-id and dynamic date
url = f"https://www.drikpanchang.com/muhurat/hora.html?geoname-id={geoname_id}&date={date_str}"

# Setup Chrome
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])

driver = webdriver.Chrome(options=chrome_options)

try:
    driver.get(url)
    time.sleep(6)
    
    print(f"\n🕉️  {driver.title}")
    print("=" * 70)
    
    page_source = driver.page_source
    
    # Extract the "Running Hora" section
    running_hora_match = re.search(
        r'Running Hora.*?<div class="dpPHeaderLeftTitle">(.*?)</div>.*?(\d{1,2}:\d{2})\s*<span[^>]*>([AP]M)</span>\s*<span[^>]*>to\s*</span>.*?(\d{1,2}:\d{2})\s*<span[^>]*>([AP]M)</span>',
        page_source, re.DOTALL
    )
    
    # Extract all hora entries from the table
    # Pattern: "Planet - Nature" followed by time range
    hora_pattern = r'<span class="dpVerticalMiddleText">(Jupiter|Mars|Sun|Venus|Mercury|Moon|Saturn)\s*-\s*(Fruitful|Aggressive|Vigorous|Beneficial|Quick|Gentle|Sluggish).*?</span>.*?<span class="dpVerticalMiddleText">(\d{1,2}:\d{2})\s*<span[^>]*>([AP]M)</span>\s*<span[^>]*>to\s*</span>.*?(\d{1,2}:\d{2})\s*<span[^>]*>([AP]M)</span>'
    
    matches = re.findall(hora_pattern, page_source, re.DOTALL)
    
    # Planet emojis
    emojis = {"Sun": "☀️", "Moon": "🌙", "Mars": "♂️", "Mercury": "☿", 
              "Jupiter": "♃", "Venus": "♀️", "Saturn": "♄"}
    
    # Build hora schedule
    hora_schedule = []
    for planet, nature, start_time, start_ampm, end_time, end_ampm in matches:
        hora_schedule.append({
            'planet': planet,
            'nature': nature,
            'start': f"{start_time} {start_ampm}",
            'end': f"{end_time} {end_ampm}",
            'start_time': start_time,
            'start_ampm': start_ampm,
            'end_time': end_time,
            'end_ampm': end_ampm
        })
    
    # Current time
    now = datetime.now()
    current_time_str = now.strftime("%I:%M %p")
    
    def time_to_minutes(time_str, ampm):
        """Convert time to minutes since midnight"""
        parts = time_str.split(':')
        hour, minute = int(parts[0]), int(parts[1])
        if ampm == 'PM' and hour != 12:
            hour += 12
        elif ampm == 'AM' and hour == 12:
            hour = 0
        return hour * 60 + minute
    
    current_minutes = now.hour * 60 + now.minute
    
    # Find current hora
    current_hora = None
    next_hora = None
    
    for i, hora in enumerate(hora_schedule):
        start_mins = time_to_minutes(hora['start_time'], hora['start_ampm'])
        end_mins = time_to_minutes(hora['end_time'], hora['end_ampm'])
        
        # Handle overnight
        if end_mins < start_mins:
            end_mins += 24 * 60
            if current_minutes < 12 * 60:  # If current time is early morning
                check_mins = current_minutes + 24 * 60
            else:
                check_mins = current_minutes
        else:
            check_mins = current_minutes
        
        if start_mins <= check_mins < end_mins:
            current_hora = hora
            if i + 1 < len(hora_schedule):
                next_hora = hora_schedule[i + 1]
            break
    
    # ============================================
    # 1. CURRENT HORA
    # ============================================
    print(f"\n⏰ Current Time: {current_time_str}")
    print("\n" + "🔮 " + "═" * 66)
    print("   1. CURRENT RUNNING HORA")
    print("═" * 70)
    
    if running_hora_match:
        planet_nature = running_hora_match.group(1)
        start_t = f"{running_hora_match.group(2)} {running_hora_match.group(3)}"
        end_t = f"{running_hora_match.group(4)} {running_hora_match.group(5)}"
        
        planet = planet_nature.split(' - ')[0].strip()
        nature = planet_nature.split(' - ')[1].strip() if ' - ' in planet_nature else ""
        emoji = emojis.get(planet, "🌟")
        
        print(f"\n   ⏰ RIGHT NOW: {emoji} {planet.upper()} HORA")
        print(f"   🕐 Time: {start_t} to {end_t}")
        print(f"   ✨ Nature: {nature}")
        
        if planet in ['Jupiter', 'Venus', 'Mercury', 'Moon']:
            print(f"\n   ✅ GOOD TIME for important activities!")
        elif planet == 'Sun':
            print(f"\n   🔸 NEUTRAL - Good for authority/govt matters")
        else:
            print(f"\n   ⚠️  CAUTION - Avoid starting new important tasks")
    elif current_hora:
        emoji = emojis.get(current_hora['planet'], "🌟")
        print(f"\n   ⏰ RIGHT NOW: {emoji} {current_hora['planet'].upper()} HORA")
        print(f"   🕐 Time: {current_hora['start']} to {current_hora['end']}")
        print(f"   ✨ Nature: {current_hora['nature']}")
    else:
        print("\n   Could not determine current hora")
    
    if next_hora:
        next_emoji = emojis.get(next_hora['planet'], "🌟")
        print(f"\n   ⏭️  Next: {next_emoji} {next_hora['planet']} ({next_hora['start']} to {next_hora['end']})")
    
    # ============================================
    # 2. JUPITER HORA TIMES
    # ============================================
    print("\n" + "♃ " + "═" * 67)
    print("   2. JUPITER (GURU) HORA - Today's Schedule")
    print("═" * 70)
    
    jupiter_horas = [h for h in hora_schedule if h['planet'] == 'Jupiter']
    
    print(f"\n   🌟 Jupiter Hora is the MOST AUSPICIOUS time for:")
    print("      • Starting new ventures & businesses")
    print("      • Education & learning")
    print("      • Legal matters & signing contracts")
    print("      • Spiritual activities & prayers")
    
    print(f"\n   📅 Today's Jupiter Hora Times:")
    print("   " + "-" * 45)
    
    for jh in jupiter_horas:
        print(f"   ♃ {jh['start']} to {jh['end']}")
    
    # ============================================
    # FULL SCHEDULE
    # ============================================
    print("\n" + "📋 " + "═" * 66)
    print("   FULL HORA SCHEDULE (Austin, TX)")
    print("═" * 70)
    
    day_horas = hora_schedule[:12] if len(hora_schedule) >= 12 else hora_schedule
    night_horas = hora_schedule[12:24] if len(hora_schedule) >= 24 else hora_schedule[12:]
    
    print("\n   ☀️ DAY HORA (Sunrise → Sunset):")
    print("   " + "-" * 55)
    for i, hora in enumerate(day_horas):
        emoji = emojis.get(hora['planet'], "🌟")
        good = "✓" if hora['planet'] in ['Jupiter', 'Venus', 'Mercury', 'Moon'] else ("~" if hora['planet'] == 'Sun' else "✗")
        print(f"   {i+1:2}. {hora['start']:>8} - {hora['end']:>8}  {emoji} {hora['planet']:<8} [{good}]")
    
    if night_horas:
        print("\n   🌙 NIGHT HORA (Sunset → Sunrise):")
        print("   " + "-" * 55)
        for i, hora in enumerate(night_horas):
            emoji = emojis.get(hora['planet'], "🌟")
            good = "✓" if hora['planet'] in ['Jupiter', 'Venus', 'Mercury', 'Moon'] else ("~" if hora['planet'] == 'Sun' else "✗")
            print(f"   {i+1:2}. {hora['start']:>8} - {hora['end']:>8}  {emoji} {hora['planet']:<8} [{good}]")
    
    print("\n" + "═" * 70)
    print("   Legend: ✓ Good | ~ Neutral | ✗ Avoid")
    print("═" * 70 + "\n")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    
finally:
    driver.quit()
