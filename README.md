# 🕉️ Hora Scraper

A Python script that fetches **Hora (planetary hour)** timings from [Drik Panchang](https://www.drikpanchang.com) for any location worldwide.

## What is Hora?

In Vedic astrology, each hour of the day is ruled by a specific planet. These planetary hours (**Hora**) influence the auspiciousness of activities:

| Planet | Nature | Best For |
|--------|--------|----------|
| ♃ Jupiter | Fruitful | New ventures, education, legal matters, spiritual activities |
| ♀️ Venus | Beneficial | Arts, relationships, luxury purchases |
| ☿ Mercury | Quick | Communication, business, travel |
| 🌙 Moon | Gentle | Emotional matters, public dealings |
| ☀️ Sun | Vigorous | Government work, authority matters |
| ♂️ Mars | Aggressive | Avoid starting new tasks |
| ♄ Saturn | Sluggish | Avoid important activities |

## Features

- 🔮 Shows **current running Hora** with recommendations
- ♃ Highlights **Jupiter Hora** times (most auspicious)
- 📋 Displays **full 24-hour schedule** (day + night)
- 🌍 Supports **any location** via geoname ID
- 📅 Uses **today's date** automatically

## Requirements

- Python 3.7+
- Google Chrome browser
- ChromeDriver (matching your Chrome version)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/msathia/HoraDetails.git
   cd HoraDetails
   ```

2. Install dependencies:
   ```bash
   pip install selenium
   ```

3. Ensure ChromeDriver is installed and in your PATH

## Usage

```bash
python hora_scraper.py
```

### Changing Location

Edit the `geoname_id` variable in the script:

```python
geoname_id = 4671654  # Austin, TX (default)
```

#### Available Geoname IDs

**USA:**
| City | Geoname ID |
|------|------------|
| Austin, TX | 4671654 |
| San Diego, CA | 5391811 |
| Los Angeles, CA | 5368361 |
| New York, NY | 5128581 |
| Chicago, IL | 4887398 |
| Houston, TX | 4699066 |
| San Francisco, CA | 5391959 |

**India:**
| City | Geoname ID |
|------|------------|
| Chennai | 1264527 |
| Hyderabad | 1269843 |
| Mumbai | 1275339 |
| Bangalore | 1277333 |
| Delhi | 1273294 |
| Kolkata | 1275004 |

**Other:**
| City | Geoname ID |
|------|------------|
| London, UK | 2643743 |
| Sydney, AU | 2147714 |
| Singapore | 1880252 |

> 💡 **Finding other cities:** Visit [drikpanchang.com](https://www.drikpanchang.com), search for your city, and copy the `geoname-id` from the URL.

## Sample Output

```
🕉️  Hora | Planetary Hours | Choghadiya

⏰ Current Time: 10:30 AM

🔮 ═══════════════════════════════════════════════════════════════════
   1. CURRENT RUNNING HORA
══════════════════════════════════════════════════════════════════════

   ⏰ RIGHT NOW: ♃ JUPITER HORA
   🕐 Time: 10:15 AM to 11:22 AM
   ✨ Nature: Fruitful

   ✅ GOOD TIME for important activities!

♃ ════════════════════════════════════════════════════════════════════
   2. JUPITER (GURU) HORA - Today's Schedule
══════════════════════════════════════════════════════════════════════

   🌟 Jupiter Hora is the MOST AUSPICIOUS time for:
      • Starting new ventures & businesses
      • Education & learning
      • Legal matters & signing contracts
      • Spiritual activities & prayers

   📅 Today's Jupiter Hora Times:
   ---------------------------------------------
   ♃ 10:15 AM to 11:22 AM
   ♃ 5:30 PM to 6:37 PM
```

## License

MIT License

## Acknowledgments

- Data sourced from [Drik Panchang](https://www.drikpanchang.com)

