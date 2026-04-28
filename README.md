# 🥗 NutriBot — AI Nutrition Assistant

**Epitech Paris — B-AIA-210 Module Project**

## 🎯 What is NutriBot?

NutriBot is an AI-powered nutrition assistant built for the 
French mass retail market. It analyzes food products using 
the Open Food Facts database and answers nutritional questions 
through a local LLM (LMStudio).

Three interfaces are available:
- 🤖 **Telegram Bot** — conversational assistant via Telegram
- 🌐 **Web Interface** — chat UI served by a Flask API
- 🏠 **Landing Page** — project presentation page

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| LLM | LMStudio (local, port 1234) |
| Food Data | Open Food Facts API |
| Bot | python-telegram-bot |
| Backend | Flask |
| Frontend | HTML / CSS / JS |

---

## ⚙️ Prerequisites

- Python 3.10+
- [LMStudio](https://lmstudio.ai/) with a model loaded 
  and local server running on port 1234
- A Telegram bot created via [@BotFather](https://t.me/BotFather)

---

## 🚀 Installation

```bash
git clone git@github.com:Slacknsss/NutriBot-AI-Nutrition-Assistant.git
cd NutriBot-AI-Nutrition-Assistant/bot
pip install -r requirements.txt
```

Create a `.env` file inside `bot/`:

```env
TELEGRAM_TOKEN=your_telegram_token
LMSTUDIO_URL=http://127.0.0.1:1234/v1
OFF_BASE_URL=https://world.openfoodfacts.org
```

---

## ▶️ Running the app

**Telegram Bot:**
```bash
python bot.py
```

**Web Interface (Flask API):**
```bash
python app.py
```

- Chat UI: `http://localhost:8080`
- Landing page: `http://localhost:8080/landing`

---

## ✨ Features

- 🔍 **Nutritional analysis** — Nutri-Score, NOVA group, 
  additives, macros
- ⚖️ **Product comparison** — side-by-side nutritional breakdown
- 🍽️ **Meal calorie estimation** (Telegram)
- 🧠 **Smart search** — fuzzy matching, abbreviations, 
  product variants on Open Food Facts
- 💬 **Conversation history** per session

**Telegram commands:**

| Command | Description |
|---|---|
| `/start` | Start the bot |
| `/nutri <product>` | Get nutritional info |
| `/comparer <A> vs <B>` | Compare two products |
| `/reset` | Reset conversation |
| `/ping` | Test connection |
| `/testapi` | Diagnose Open Food Facts API |

---

## 📁 Project Structure
├── bot/
│   ├── app.py           # Flask API + web interface
│   ├── bot.py           # Telegram bot
│   └── requirements.txt
├── site/
│   ├── index_1.html     # Web chat frontend
│   └── landing.html     # Project landing page
└── bootstrap/
└── bruno/           # Value chain analysis
---

## 📊 Data Source

Nutritional data is sourced from 
[Open Food Facts](https://world.openfoodfacts.org) — 
an open and collaborative food database.

---

## 👤 Author

**Simon Slack** — Epitech Paris (Class of 2028)  
[github.com/Slacknsss](https://github.com/Slacknsss)
