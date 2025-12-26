# 🕉️ Hora API

A FastAPI web service that provides **Hora (planetary hour)** timings from [Drik Panchang](https://www.drikpanchang.com). Deploy to Google Cloud Run for a serverless, scalable API.

## What is Hora?

In Vedic astrology, each hour of the day is ruled by a specific planet. These planetary hours (**Hora**) influence the auspiciousness of activities:

| Planet | Nature | Quality | Best For |
|--------|--------|---------|----------|
| ♃ Jupiter | Fruitful | ✅ Good | New ventures, education, legal matters, spiritual activities |
| ♀️ Venus | Beneficial | ✅ Good | Arts, relationships, luxury purchases |
| ☿ Mercury | Quick | ✅ Good | Communication, business, travel |
| 🌙 Moon | Gentle | ✅ Good | Emotional matters, public dealings |
| ☀️ Sun | Vigorous | 🔸 Neutral | Government work, authority matters |
| ♂️ Mars | Aggressive | ⚠️ Avoid | Avoid starting new tasks |
| ♄ Saturn | Sluggish | ⚠️ Avoid | Avoid important activities |

---

## 🚀 API Endpoints

### `GET /`
Welcome message and list of available endpoints.

### `GET /health`
Health check endpoint for Cloud Run.

### `GET /locations`
List all preset locations with their geoname IDs.

### `GET /hora`
Get full hora schedule for a location.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `location` | string | Preset location name (e.g., `austin`, `chennai`) |
| `geoname_id` | integer | Custom geoname ID from drikpanchang.com |
| `date` | string | Date in DD/MM/YYYY format (defaults to today) |

**Examples:**
```bash
# Using preset location
curl "https://your-service.run.app/hora?location=austin"

# Using custom geoname ID
curl "https://your-service.run.app/hora?geoname_id=1264527"

# Specific date
curl "https://your-service.run.app/hora?location=chennai&date=25/12/2025"
```

### `GET /hora/current`
Get only the current running hora (lightweight response).

```bash
curl "https://your-service.run.app/hora/current?location=austin"
```

### `GET /hora/jupiter`
Get Jupiter (most auspicious) hora times for the day.

```bash
curl "https://your-service.run.app/hora/jupiter?location=chennai"
```

---

## 📍 Available Locations

**USA:**
- `austin` - Austin, TX
- `san_diego` - San Diego, CA
- `los_angeles` - Los Angeles, CA
- `new_york` - New York, NY
- `chicago` - Chicago, IL
- `houston` - Houston, TX
- `san_francisco` - San Francisco, CA

**India:**
- `chennai` - Chennai
- `hyderabad` - Hyderabad
- `mumbai` - Mumbai
- `bangalore` - Bangalore
- `delhi` - Delhi
- `kolkata` - Kolkata

**Other:**
- `london` - London, UK
- `sydney` - Sydney, Australia
- `singapore` - Singapore

> 💡 **Custom locations:** Find your city's geoname ID on [drikpanchang.com](https://www.drikpanchang.com) and use the `geoname_id` parameter.

---

## 🏃 Running Locally

### Prerequisites
- Python 3.9+
- Google Chrome browser
- ChromeDriver

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/msathia/HoraDetails.git
   cd HoraDetails
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the API:
   ```bash
   python main.py
   ```

4. Open http://localhost:8080/docs for interactive API documentation.

---

## ☁️ Deploy to Google Cloud Run

### Prerequisites
- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) installed
- A Google Cloud project with billing enabled
- Cloud Run API enabled

### Step 1: Authenticate with Google Cloud
```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### Step 2: Enable required APIs
```bash
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

### Step 3: Build and deploy
```bash
# Build the container image
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/hora-api

# Deploy to Cloud Run
gcloud run deploy hora-api \
  --image gcr.io/YOUR_PROJECT_ID/hora-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --timeout 60s
```

### Step 4: Get your service URL
After deployment, you'll receive a URL like:
```
https://hora-api-xxxxxxxxxx-uc.a.run.app
```

Test it:
```bash
curl "https://hora-api-xxxxxxxxxx-uc.a.run.app/hora?location=austin"
```

---

## 📊 Sample API Response

```json
{
  "success": true,
  "title": "December 25, 2025 Shubha Horai...",
  "date": "25/12/2025",
  "geoname_id": 4671654,
  "current_time": "07:03 PM",
  "current_hora": {
    "planet": "Saturn",
    "nature": "Sluggish",
    "emoji": "♄",
    "quality": "avoid",
    "start": "06:46 PM",
    "end": "07:55 PM"
  },
  "next_hora": {
    "planet": "Jupiter",
    "nature": "Fruitful",
    "emoji": "♃",
    "quality": "good",
    "start": "07:55 PM",
    "end": "09:04 PM"
  },
  "jupiter_horas": [...],
  "day_horas": [...],
  "night_horas": [...],
  "full_schedule": [...]
}
```

---

## 📁 Project Structure

```
HoraDetails/
├── main.py              # FastAPI application
├── hora_scraper.py      # Original CLI scraper
├── requirements.txt     # Python dependencies
├── Dockerfile           # Container configuration
└── README.md            # Documentation
```

---

## 📖 Interactive API Docs

Once running, visit:
- **Swagger UI:** `http://localhost:8080/docs`
- **ReDoc:** `http://localhost:8080/redoc`

---

## License

MIT License

## Acknowledgments

- Data sourced from [Drik Panchang](https://www.drikpanchang.com)
