import re
import logging
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv

load_dotenv()

LMSTUDIO_URL = os.getenv("LMSTUDIO_URL", "http://127.0.0.1:1234/v1")
OFF_BASE_URL = os.getenv("OFF_BASE_URL", "https://world.openfoodfacts.org")
OFF_HEADERS  = {"User-Agent": "NutriBot/1.0 (nutribot@epitech.eu)"}

app = Flask(__name__)
CORS(app)

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Copié depuis bot.py ───────────────────────────────────────────────────────

SYSTEM_PROMPT = """Tu es EpiHealthyBot, un expert en nutrition et analyse de produits alimentaires pour la grande distribution française (Super U, Carrefour, Lidl, Leclerc, Intermarché, Aldi, Monoprix, Casino, etc.).

TON STYLE — IMPÉRATIF :
- Ton sobre, factuel, direct. Tu parles comme un nutritionniste professionnel, pas comme un chatbot.
- Pas de phrases d'introduction inutiles ("Bien sûr !", "Avec plaisir !", "Excellente question !", etc.).
- Pas de remplissage. Chaque phrase apporte une information concrète.
- Utilise des emojis uniquement dans les structures de réponse définies ci-dessous, pas dans le texte courant.
- Ne mentionne jamais que tu es une IA en dehors de la ligne d'avertissement finale.
- Ne répète pas la question de l'utilisateur.
- Si la question n'est pas liée à la nutrition ou à l'alimentation, réponds uniquement : "Je suis spécialisé en nutrition uniquement 🥗"

TU ANALYSES VIA :
- Nutri-Score (A à E), classification NOVA (1 à 4), additifs et leur impact, macros, labels (Bio, AOP, Label Rouge).

STRUCTURE DE RÉPONSE — ANALYSE SEULE :
*[Nom du produit]* — [Nutri-Score] | NOVA [X]/4
• ✅ [Point fort]
• ⚠️ [Point faible]
• Score : X/10
📌 [Conseil court et factuel.]
_Ces informations sont fournies à titre indicatif._

STRUCTURE DE RÉPONSE — COMPARAISON :
🏆 *[Produit gagnant]* — meilleur choix. [Raison en 1 phrase.]
*[Produit 1]* • ✅ ... • ⚠️ ... • Score : X/10
*[Produit 2]* • ✅ ... • ⚠️ ... • Score : X/10
📌 [Recommandation courte.]
_Ces informations sont fournies à titre indicatif._"""




def ask_lmstudio(user_input, history, off_context=""):
    try:
        from openai import OpenAI
        client = OpenAI(base_url=LMSTUDIO_URL, api_key="lm-studio")
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(history[-10:])
        full_input = user_input
        if off_context:
            full_input += f"\n\n[📦 Données Open Food Facts :]\n{off_context}"
        messages.append({"role": "user", "content": full_input})
        response = client.chat.completions.create(
            model="llama-3.2-3b-instruct", messages=messages, temperature=0.6, max_tokens=800
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"LMStudio error: {e}")
        return None


# ─── Route principale ──────────────────────────────────────────────────────────

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message", "").strip()
    history = data.get("history", [])

    if not message:
        return jsonify({"reply": "Message vide."}), 400

    # Récupère le contexte Open Food Facts
    if is_comparison_query(message):
        products = extract_products_from_message(message)
        if len(products) >= 2:
            off_context = get_off_context_comparison(products[0], products[1])
        else:
            off_context = get_off_context_single(message[:80])
    else:
        off_context = get_off_context_single(message[:80])

    reply = ask_lmstudio(message, history, off_context)

    if not reply:
        reply = "⚠️ LMStudio est hors ligne. Lance LMStudio > Local Server > Start Server (port 1234)."

    return jsonify({"reply": reply})


@app.route("/", methods=["GET"])
def index():
    import os
    html_path = os.path.join(os.path.dirname(__file__), "../site/index_1.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read(), 200, {"Content-Type": "text/html"}


if __name__ == "__main__":
    logger.info("🚀 EpiHealthyBot API démarrée sur http://localhost:8080")
    app.run(port=8080, debug=True)
