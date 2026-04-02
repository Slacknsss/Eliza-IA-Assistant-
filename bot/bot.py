import logging
import requests
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
LMSTUDIO_URL = os.getenv("LMSTUDIO_URL", "http://127.0.0.1:1234/v1")
OFF_BASE_URL = os.getenv("OFF_BASE_URL", "https://world.openfoodfacts.org")

SYSTEM_PROMPT = """Tu es NutriBot, un assistant IA spécialisé en nutrition et alimentation.
Tu réponds en français, de façon concise et bienveillante.
Tu aides les utilisateurs à comprendre les valeurs nutritionnelles des produits alimentaires,
notamment les produits industriels de grande surface (Carrefour, Super U, Leclerc, etc.).
Tu peux comparer des produits, analyser leur Nutri-Score, leurs additifs, et donner des conseils nutritionnels.
Si des données Open Food Facts te sont fournies, utilise-les pour répondre précisément.
Si tu ne sais pas, dis-le honnêtement."""

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)
ADDITIVE_RISK = {
    "en:e102": "⚠️ colorant controversé",
    "en:e110": "⚠️ colorant controversé",
    "en:e621": "⚠️ exhausteur de goût (MSG)",
    "en:e951": "⚠️ aspartame",
    "en:e211": "⚠️ conservateur (benzoate)",
    "en:e330": "✅ acide citrique",
    "en:e322": "✅ lécithine",
}


def search_products(query: str, max_results: int = 3) -> list:
    try:
        params = {
            "search_terms": query,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": max_results,
            "fields": "product_name,brands,nutriscore_grade,nutriments,additives_tags,quantity",
            "lc": "fr",
            "cc": "fr",
        }
        r = requests.get(f"{OFF_BASE_URL}/cgi/search.pl", params=params, timeout=10)
        r.raise_for_status()
        return r.json().get("products", [])[:max_results]
    except Exception as e:
        logger.error(f"OpenFoodFacts error: {e}")
        return []


def format_product(product: dict) -> str:
    if not product:
        return ""
    name     = product.get("product_name") or "Nom inconnu"
    brand    = product.get("brands") or "Marque inconnue"
    quantity = product.get("quantity") or "N/A"
    ns_grade = (product.get("nutriscore_grade") or "n/a").lower()
    ns_emoji = NUTRISCORE_EMOJI.get(ns_grade, "❓")
    n        = product.get("nutriments", {})
    additives_raw = product.get("additives_tags", [])
    additives_str = ", ".join(
        f"{a.replace('en:', '').upper()} {ADDITIVE_RISK.get(a, '')}".strip()
        for a in additives_raw[:5]
    ) if additives_raw else "Aucun"
    return (
        f"Produit: {name} ({brand}) — {quantity}\n"
        f"Nutri-Score: {ns_emoji} {ns_grade.upper()}\n"
        f"Calories: {n.get('energy-kcal_100g', 'N/A')} kcal | "
        f"Protéines: {n.get('proteins_100g', 'N/A')}g | "
        f"Glucides: {n.get('carbohydrates_100g', 'N/A')}g | "
        f"Lipides: {n.get('fat_100g', 'N/A')}g | "
        f"Sel: {n.get('salt_100g', 'N/A')}g\n"
        f"Additifs: {additives_str}"
    )


def get_off_context(query: str) -> str:
    products = search_products(query, max_results=3)
    if not products:
        return ""
    parts = [format_product(p) for p in products if p.get("product_name")]
    return "\n---\n".join(parts) if parts else ""


def ask_lmstudio(user_input: str, history: list, off_context: str = "") -> str | None:
    try:
        from openai import OpenAI
        client = OpenAI(base_url=LMSTUDIO_URL, api_key="lm-studio")

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(history[-10:])

        if off_context:
            full_input = f"{user_input}\n\n[Données Open Food Facts :]\n{off_context}"
        else:
            full_input = user_input

        messages.append({"role": "user", "content": full_input})

        response = client.chat.completions.create(
            model="local-model",
            messages=messages,
            temperature=0.7,
            max_tokens=600,
        )
        return response.choices[0].message.content.strip()
    except Exception as error:
        logger.warning(f"LMStudio inaccessible : {error}")
        return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["history"] = []
    await update.message.reply_text(
        "👋 Bonjour ! Je suis *NutriBot* 🥗, votre assistant nutritionnel IA.\n\n"
        "Posez-moi vos questions sur l'alimentation, les produits, les Nutri-Scores...\n\n"
        "Commandes :\n"
        "• `/ping` — tester la connexion\n"
        "• `/nutri <produit>` — recherche directe Open Food Facts\n"
        "• `/reset` — réinitialiser la conversation\n"
        "• `/help` — afficher ce message\n"
        "• Ou écrivez simplement ici pour me parler ! 💬",
        parse_mode="Markdown",
    )


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 pong")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["history"] = []
    await update.message.reply_text("🔄 Conversation réinitialisée.")


async def nutri_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Usage : `/nutri <produit>`\nEx : `/nutri Nutella`",
            parse_mode="Markdown",
        )
        return
    query = " ".join(context.args)
    await update.message.chat.send_action("typing")
    off_context = get_off_context(query)
    if off_context:
        await update.message.reply_text(f"```\n{off_context}\n```", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"😕 Aucun produit trouvé pour *{query}*.", parse_mode="Markdown")


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    history = context.user_data.setdefault("history", [])

    await update.message.chat.send_action("typing")

    off_context = get_off_context(user_message)
    reply = ask_lmstudio(user_message, history, off_context)

    if not reply:
        reply = (
            "⚠️ *Service IA Hors Ligne*\n\n"
            "Démarrez LMStudio (Local Server, port 1234).\n"
            f"_Vous aviez écrit :_ \"{user_message}\""
        )

    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": reply})

    if len(history) > 20:
        context.user_data["history"] = history[-20:]

    await update.message.reply_text(reply, parse_mode="Markdown")


def main():
    logger.info("Démarrage NutriBot...")
    logger.info(f"LMStudio : {LMSTUDIO_URL}")

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ping", ping))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(CommandHandler("nutri", nutri_cmd))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    application.run_polling()


if __name__ == "__main__":
    main()