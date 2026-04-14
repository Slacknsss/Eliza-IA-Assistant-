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


NUTRISCORE_EMOJI = {"a": "🟢 A", "b": "🟡 B", "c": "🟠 C", "d": "🔴 D", "e": "⚫ E"}                                  
ADDITIVE_RISK = {                                                                                                     
      "en:e102": "⚠️  Tartrazine", "en:e211": "⚠️  Benzoate de sodium",                                                   
      "en:e250": "⚠️  Nitrite de sodium", "en:e621": "⚠️  Glutamate (MSG)",                                               
      "en:e951": "⚠️  Aspartame", "en:e330": "✅ Acide citrique", "en:e322": "✅ Lécithine",                             
  }                                                                                                                     
COMPARISON_KEYWORDS = [                                                                                               
      r"entre\b", r"vs\b", r"versus\b", r"comparer?\b", r"comparaison",                                                 
      r"lequel", r"laquelle", r"quel.*meilleur", r"j.hésite", r"différence",                                            
  ]                                                                                                                     
                                                                                                                        
def is_comparison_query(text):                                                                                        
      return any(re.search(kw, text.lower()) for kw in COMPARISON_KEYWORDS)
                                                                                                                        
def extract_products_from_message(text):                                                                              
      match = re.search(r"entre\s+(.+?)\s+(?:et|ou|vs|versus)\s+(.+?)(?:\s*\?.*)?$", text, re.IGNORECASE)
      if match:                                                                                                         
          return [match.group(1).strip(), match.group(2).strip()]
      parts = re.split(r"\s+(?:et|ou|vs|versus)\s+", text, flags=re.IGNORECASE)                                         
      if len(parts) >= 2:                                                                                               
          return [p.strip() for p in parts[:2] if len(p.strip()) > 3]
      return []                                                                                                         
                  
def search_products(query, max_results=2, worldwide=False):                                                           
      try:        
          params = {                                                                                                    
              "search_terms": query, "search_simple": 1, "action": "process",
              "json": 1, "page_size": max_results,                                                                      
              "fields":                                                                                                 
  "product_name,brands,nutriscore_grade,nova_group,nutriments,additives_tags,quantity,labels_tags",                     
          }                                                                                                             
          if not worldwide:                                                                                             
              params["lc"] = "fr"                                                                                       
          r = requests.get(f"{OFF_BASE_URL}/cgi/search.pl", params=params, headers=OFF_HEADERS, timeout=10)
          r.raise_for_status()                                                                                          
          return [p for p in r.json().get("products", [])[:max_results] if p.get("product_name")]                       
      except Exception as e:                                                                                            
          logger.error(f"OFF error: {e}")                                                                               
          return []                                                                                                     
                  
def format_product(product):
      if not product:
          return ""                                                                                                     
      name  = product.get("product_name") or "Nom inconnu"
      brand = product.get("brands") or "Marque inconnue"                                                                
      ns    = NUTRISCORE_EMOJI.get((product.get("nutriscore_grade") or "").lower(), "❓")                               
      nova  = product.get("nova_group") or "N/A"
      n     = product.get("nutriments", {})                                                                             
      bio   = "🌿 BIO" if any("organic" in l or "bio" in l for l in product.get("labels_tags", [])) else ""
      adds  = product.get("additives_tags", [])                                                                         
      adds_str = ", ".join(
          f"{a.replace('en:','').upper()} {ADDITIVE_RISK.get(a,'')}".strip() for a in adds[:5]                          
      ) if adds else "Aucun additif ✅"                                                                                 
      return (                                                                                                          
          f"Produit : {name} ({brand}) {bio}\n"                                                                         
          f"Nutri-Score : {ns} | NOVA : {nova}/4\n"                                                                     
          f"Calories : {n.get('energy-kcal_100g','N/A')} kcal/100g | "
          f"Protéines : {n.get('proteins_100g','N/A')}g | "                                                             
          f"Glucides : {n.get('carbohydrates_100g','N/A')}g | "
          f"Lipides : {n.get('fat_100g','N/A')}g | Sel : {n.get('salt_100g','N/A')}g\n"                                 
          f"Additifs : {adds_str}"                                                                                      
      )                                                                                                                 
                                                                                                                        
def get_off_context_single(query):                                                                                    
      products = search_products(query, max_results=2)
      if not products:                                                                                                  
          products = search_products(query, max_results=2, worldwide=True)
      parts = [format_product(p) for p in products if p.get("product_name")]                                            
      return "\n---\n".join(parts) if parts else ""                                                                     
                                                                                                                        
def get_off_context_comparison(a, b):                                                                                 
      ctx_a = get_off_context_single(a)
      ctx_b = get_off_context_single(b)                                                                                 
      result = ""
      if ctx_a:                                                                                                         
          result += f"=== {a} ===\n{ctx_a}\n\n"
      if ctx_b:                                                                                                         
          result += f"=== {b} ===\n{ctx_b}"
      return result.strip()

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

@app.route("/landing", methods=["GET"])
def landing():
    html_path = os.path.join(os.path.dirname(__file__), "../site/landing.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read(), 200, {"Content-Type": "text/html"}

if __name__ == "__main__":
    logger.info("🚀 EpiHealthyBot API démarrée sur http://localhost:8080")
    app.run(port=8080, debug=True)
