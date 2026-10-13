# NutriBot (Eliza project)

Epitech Paris, B-AIA-210. Team of three: Simon Slack, Bruno Delporte, Bilel Ouites.

A nutrition assistant for French supermarket products. It looks products up on Open Food Facts and passes the data to a local LLM running in LMStudio, which writes the answer. Two ways to use it: a Telegram bot, and a web chat served by a small Flask API. There is also a landing page, made for the business part of the module.

## Who did what

- Bruno Delporte: first version of the Telegram bot and its commands, value chain analysis in `bootstrap/bruno/`
- Bilel Ouites: Open Food Facts integration in the Flask API (search, formatting, nutrition context)
- Simon Slack: Flask API and its LMStudio calls, web chat (`site/index_1.html`), landing page, cleanup of the bot, README

## Stack

Python 3.10+, LMStudio (local server on port 1234, OpenAI-compatible API), Open Food Facts API, python-telegram-bot, Flask, plain HTML/CSS/JS.

## Setup

You need LMStudio with a model loaded and the local server started on port 1234, and a Telegram bot token from [@BotFather](https://t.me/BotFather) if you want the bot.

```bash
git clone https://github.com/Slacknsss/Eliza-IA-Assistant-.git
cd Eliza-IA-Assistant-/bot
pip install -r requirements.txt
```

Create `bot/.env`:

```env
TELEGRAM_TOKEN=your_telegram_token
LMSTUDIO_URL=http://127.0.0.1:1234/v1
OFF_BASE_URL=https://world.openfoodfacts.org
```

## Run

```bash
python bot.py   # Telegram bot
python app.py   # web chat on http://localhost:8080, landing on /landing
```

## What it does

- Product sheet from Open Food Facts: Nutri-Score, NOVA group, additives, macros
- Compares two products, with `/comparer A vs B` or just "A vs B" in the chat
- The web API retries the search worldwide when nothing is found in France
- Keeps the last messages of the conversation as context for the LLM
- Meal calorie estimates are answered by the LLM alone, without Open Food Facts data

Telegram commands: `/start`, `/help`, `/nutri <product>`, `/comparer <A> vs <B>`, `/reset`, `/ping`.

## Structure

```
bot/
  app.py            Flask API + web chat
  bot.py            Telegram bot
  requirements.txt
site/
  index_1.html      web chat
  landing.html      landing page (pricing is a mockup, nothing is sold)
  demo.mp4
bootstrap/bruno/    value chain analysis
```
