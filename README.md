# 🧠 CognitoFeed

> **🚧 Work in Progress**
> 
> `[█░░░░░░░░░]` 10% — Early development stage

---

An intelligent RSS reader powered by AI (Google Gemini).

## Features
- 📰 RSS/Atom feed subscriptions
- 💬 Automatic AI summaries (short & medium)
- 🎭 Article sentiment analysis
- 📌 Trend detection across articles
- ⭐ Favourite articles
- 📖 Reader View (distraction-free reading)
- 🔔 New article notifications
- 🔄 Auto-refresh feeds
- 🤖 AI chat with article context

## Requirements
- Python 3.11+
- Google AI Studio API key (Gemini)

## Installation

```bash
git clone https://github.com/AnonBOTpl/CognitoFeed.git
cd CognitoFeed
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file:
```
GEMINI_API_KEY=your_api_key_here
```

## Running

```bash
# First run – fetch initial articles
python main.py

# Start the server
uvicorn api:app --reload
```

Open http://localhost:8000 in your browser.

## Tech Stack
- **Backend:** Python + FastAPI
- **Database:** SQLite
- **AI:** Google Gemini 2.5 Flash
- **Frontend:** HTML/CSS/JS
