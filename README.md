# 🚁 Skylark Drones Operations Coordinator

An AI-powered operations management system for drone fleet coordination, pilot assignments, and mission tracking. Built with Streamlit and powered by Groq LLM.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28-red)
![Groq](https://img.shields.io/badge/LLM-Groq-green)

## ✨ Features

### 🧑‍✈️ Pilot Management
- Query pilots by skills, location, certifications, and availability
- Update pilot status (Available, Assigned, On Leave, Unavailable)
- Calculate mission costs based on pilot daily rates
- Track current assignments and availability dates

### ✈️ Drone Fleet Management
- Query drones by capabilities (RGB, Thermal, LiDAR, Multispectral)
- Filter by weather compatibility (Sunny, Cloudy, Rainy, Windy)
- Track drone status and maintenance schedules
- Monitor battery life and flight hours

### 📋 Assignment Tracking
- Auto-match pilots and drones to missions based on requirements
- Track active missions with start/end dates
- Budget monitoring and cost tracking
- Real-time status updates synced to Google Sheets

### ⚠️ Conflict Detection
- Double booking detection for pilots and drones
- Skill mismatch identification
- Budget overrun warnings
- Weather compatibility checks

### 🔄 Two-Way Google Sheets Sync
- Real-time data synchronization
- Automatic status updates reflected in spreadsheets
- Dynamic column detection for flexible sheet structures

## 🛠️ Tech Stack

- **Frontend**: Streamlit
- **AI/LLM**: Groq (llama-3.3-70b-versatile)
- **Database**: Google Sheets API v4
- **Language**: Python 3.12

## 📋 Prerequisites

- Python 3.10+
- Google Cloud Project with Sheets API enabled
- Groq API key

## 🚀 Installation

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/skylark-drone-ops.git
cd skylark-drone-ops
```

### 2. Create virtual environment
```bash
python -m venv venv

# Windows
.\venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
Create a `.env` file in the project root:
```env
GROQ_API_KEY=your_groq_api_key_here
PILOT_ROSTER_SHEET_ID=your_pilot_sheet_id
DRONE_FLEET_SHEET_ID=your_drone_sheet_id
MISSIONS_SHEET_ID=your_missions_sheet_id
```

### 5. Set up Google Sheets credentials
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable **Google Sheets API**
4. Create **OAuth 2.0 credentials** (Desktop application)
5. Download credentials and save as `credential.json` in project root

### 6. Run the application
```bash
streamlit run app.py
```

## 📊 Google Sheets Structure

### Pilot Roster Sheet
| Column | Description |
|--------|-------------|
| pilot_id | Unique identifier (P001, P002...) |
| name | Pilot full name |
| skills | Comma-separated skills (Mapping, Survey, Inspection, Thermal) |
| certifications | Certifications (DGCA, Night Ops, etc.) |
| location | Base location |
| status | Available, Assigned, On Leave, Unavailable |
| current_assignment | Current project ID or empty |
| available_from | Date available |
| daily_rate_inr | Daily rate in INR |

### Drone Fleet Sheet
| Column | Description |
|--------|-------------|
| drone_id | Unique identifier (D001, D002...) |
| model | Drone model name |
| capabilities | Camera/sensor capabilities |
| location | Current location |
| status | Available, In Use, Maintenance |
| weather_compatibility | Suitable weather conditions |
| current_assignment | Current project ID or empty |
| battery_cycles | Total battery cycles |
| last_maintenance | Last maintenance date |

### Missions Sheet
| Column | Description |
|--------|-------------|
| project_id | Unique project identifier |
| client_name | Client name |
| location | Mission location |
| mission_type | Type of mission |
| required_skills | Required pilot skills |
| required_capabilities | Required drone capabilities |
| start_date | Mission start date |
| end_date | Mission end date |
| budget_inr | Budget in INR |
| status | Planned, In Progress, Completed |
| assigned_pilot | Assigned pilot ID |
| assigned_drone | Assigned drone ID |

## 💬 Example Queries

```
"Find available pilots with Mapping skills in Bangalore"
"What drones are available for rainy weather?"
"Assign a pilot and drone to PRJ001"
"Calculate cost for pilot P001 for a 5-day mission"
"Check for conflicts in current assignments"
"Update pilot P001 status to On Leave"
```

## 🌐 Deployment

### Streamlit Community Cloud (Free)

1. Push code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repository
4. Add secrets in Settings → Secrets:

```toml
GROQ_API_KEY = "your-api-key"
PILOT_ROSTER_SHEET_ID = "sheet-id"
DRONE_FLEET_SHEET_ID = "sheet-id"
MISSIONS_SHEET_ID = "sheet-id"

[google_credentials]
type = "service_account"
project_id = "your-project"
private_key_id = "key-id"
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "service-account@project.iam.gserviceaccount.com"
client_id = "client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
```

5. Deploy!

## 📁 Project Structure

```
skylark-drone-ops/
├── app.py                  # Streamlit web interface
├── agent.py                # AI agent with Groq LLM
├── sheets_sync.py          # Google Sheets integration
├── roster_manager.py       # Pilot management logic
├── inventory_manager.py    # Drone fleet management
├── assignment_tracker.py   # Mission assignment logic
├── conflict_detector.py    # Conflict detection system
├── utils.py                # Utility functions
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (not in git)
├── credential.json         # Google OAuth credentials (not in git)
├── token.pickle           # OAuth token cache (not in git)
└── .gitignore             # Git ignore rules
```

## 🔑 API Keys

### Groq API
1. Sign up at [console.groq.com](https://console.groq.com)
2. Create an API key
3. Add to `.env` as `GROQ_API_KEY`

### Google Sheets
1. Create project at [Google Cloud Console](https://console.cloud.google.com)
2. Enable Google Sheets API
3. Create OAuth 2.0 credentials
4. Download as `credential.json`

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License.

## 👨‍💻 Author

Built for Skylark Drones Operations

---

**Note**: Ensure all sensitive files (`.env`, `credential.json`, `token.pickle`) are added to `.gitignore` before pushing to a public repository.
