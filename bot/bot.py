import logging
import re
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
LMSTUDIO_URL   = os.getenv("LMSTUDIO_URL", "http://127.0.0.1:1234/v1")
OFF_BASE_URL   = os.getenv("OFF_BASE_URL", "https://world.openfoodfacts.org")
OFF_HEADERS    = {"User-Agent": "NutriBot/1.0 (nutribot@epitech.eu)"}

SYSTEM_PROMPT = """Tu es NutriBot, un expert en nutrition et analyse de produits alimentaires pour la grande distribution française (Super U, Carrefour, Lidl, Leclerc, Intermarché, Aldi, Monoprix, Casino, etc.).

TON STYLE — IMPÉRATIF :
- Ton sobre, factuel, direct. Tu parles comme un nutritionniste professionnel, pas comme un chatbot.
- Pas de phrases d'introduction inutiles ("Bien sûr !", "Avec plaisir !", "Excellente question !", etc.).
- Pas de remplissage. Chaque phrase apporte une information concrète.
- Utilise des emojis uniquement dans les structures de réponse définies ci-dessous, pas dans le texte courant.
- Ne mentionne jamais que tu es une IA en dehors de la ligne d'avertissement finale.
- Ne répète pas la question de l'utilisateur.

TU ANALYSES VIA :
- Nutri-Score (A à E), classification NOVA (1 à 4), additifs et leur impact, macros (calories, protéines, glucides/sucres, lipides/saturés, sel, fibres), labels (Bio, AOP, Label Rouge).

STRUCTURE DE RÉPONSE — COMPARAISON (quand l'utilisateur compare deux produits) :

🏆 *[Nom du produit gagnant]* — meilleur choix. [Raison factuelle en 1 phrase.]

*[Produit 1]*
• ✅ [Point fort factuel]
• ✅ [Point fort factuel]
• ⚠️ [Point faible factuel]
• Score : X/10

*[Produit 2]*
• ✅ [Point fort factuel]
• ⚠️ [Point faible factuel]
• ⚠️ [Point faible factuel]
• Score : X/10

📌 [Recommandation courte, argumentée, sans fioritures.]
_Ces informations sont fournies à titre indicatif et ne remplacent pas l'avis d'un professionnel de santé._

STRUCTURE DE RÉPONSE — ANALYSE SEULE (un seul produit) :

*[Nom du produit]* — [Nutri-Score] | NOVA [X]/4
• ✅ [Point fort]
• ✅ [Point fort]
• ⚠️ [Point faible]
• Score : X/10

📌 [Conseil court et factuel.]
_Ces informations sont fournies à titre indicatif et ne remplacent pas l'avis d'un professionnel de santé._

STRUCTURE DE RÉPONSE — ESTIMATION CALORIQUE D'UN REPAS (quand l'utilisateur décrit un plat ou demande des calories) :
- Utilise UNIQUEMENT les données Open Food Facts fournies comme base de calcul, jamais des chiffres de mémoire.
- Estime des portions réalistes (ex : 200g de couscous cuit, 2 merguez = 100g, 1 yaourt = 125g).
- Format :

🍽️ *Estimation pour votre repas*

| Ingrédient | Portion est. | kcal |
|---|---|---|
| [Ingrédient] | Xg | ~XXX kcal |

*Total estimé : ~XXX kcal*

📌 [Note sur la précision + conseil nutritionnel bref.]
_Ces informations sont fournies à titre indicatif et ne remplacent pas l'avis d'un professionnel de santé._
"""

NUTRISCORE_EMOJI = {
    "a": "🟢 A",
    "b": "🟡 B",
    "c": "🟠 C",
    "d": "🔴 D",
    "e": "⚫ E",
    "n/a": "❓ N/A",
}

ADDITIVE_RISK = {
    "en:e102": "⚠️ Tartrazine (colorant, allergie possible)",
    "en:e110": "⚠️ Jaune orangé (colorant controversé)",
    "en:e120": "⚠️ Carmin (colorant d'origine animale)",
    "en:e129": "⚠️ Rouge allura (colorant controversé)",
    "en:e211": "⚠️ Benzoate de sodium (conservateur)",
    "en:e202": "⚠️ Sorbate de potassium (conservateur)",
    "en:e250": "⚠️ Nitrite de sodium (charcuteries, risque cancérigène)",
    "en:e621": "⚠️ Glutamate (MSG, exhausteur de goût)",
    "en:e635": "⚠️ Ribonucléotide (exhausteur de goût)",
    "en:e951": "⚠️ Aspartame (édulcorant controversé)",
    "en:e955": "⚠️ Sucralose (édulcorant)",
    "en:e950": "⚠️ Acésulfame K (édulcorant)",
    "en:e471": "⚠️ Mono- et diglycérides (émulsifiant, ultra-transformation)",
    "en:e472e": "⚠️ DATEM (émulsifiant, ultra-transformation)",
    "en:e433": "⚠️ Polysorbate 80 (émulsifiant, risques intestinaux)",
    "en:e330": "✅ Acide citrique (naturel)",
    "en:e322": "✅ Lécithine (émulsifiant naturel)",
    "en:e300": "✅ Vitamine C (antioxydant)",
    "en:e306": "✅ Vitamine E (antioxydant)",
}

COMPARISON_KEYWORDS = [
    r"entre\b", r"vs\b", r"versus\b", r"ou\b", r"comparer?\b",
    r"comparaison", r"lequel", r"laquelle", r"quel.*meilleur",
    r"j.hésite", r"j.hesite", r"différence", r"difference",
]

FRENCH_SUPERMARKETS = [
    "super u", "super-u", "carrefour", "lidl", "leclerc", "e.leclerc",
    "intermarché", "intermarche", "aldi", "monoprix", "casino", "franprix",
    "simply market", "cora", "match", "biocoop", "naturalia",
]

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def is_comparison_query(text: str) -> bool:
    text_lower = text.lower()
    return any(re.search(kw, text_lower) for kw in COMPARISON_KEYWORDS)


def extract_supermarket(text: str) -> str | None:
    text_lower = text.lower()
    for market in FRENCH_SUPERMARKETS:
        if market in text_lower:
            return market.title()
    return None


def extract_products_from_message(text: str) -> list[str]:
    cleaned = text
    for market in FRENCH_SUPERMARKETS:
        cleaned = re.sub(re.escape(market), "", cleaned, flags=re.IGNORECASE)

    match = re.search(
        r"entre\s+(.+?)\s+(?:et|ou|vs|versus)\s+(.+?)(?:\s*\?.*)?$",
        cleaned, re.IGNORECASE
    )
    if match:
        return [match.group(1).strip(), match.group(2).strip()]

    parts = re.split(r"\s+(?:et|ou|vs|versus)\s+", cleaned, flags=re.IGNORECASE)
    if len(parts) >= 2:
        return [p.strip().strip("\"'") for p in parts[:2] if len(p.strip()) > 3]

    return []


def normalize_query(query: str) -> str:
    """
    Nettoie une requête utilisateur :
    - Remplace tirets spéciaux par des espaces
    - Supprime les quantités (500g, 1L, etc.)
    - Normalise les espaces
    - Met en minuscules
    """
    query = query.replace("–", " ").replace("—", " ").replace("-", " ")
    query = re.sub(r"\b\d+\s*(?:ml|cl|l|g|kg|gr|litre|litres|L)\b", "", query, flags=re.IGNORECASE)
    query = re.sub(r"\s{2,}", " ", query).strip()
    return query.lower()


ABBREVIATIONS = {
    "fb":    "fromage blanc",
    "pt":    "petit filous",
    "yaourt": "yaourt",
    "yog":   "yaourt",
    "cc":    "crème caramel",
    "lc":    "la laitière",
    "pj":    "pur jus",
    "jus oc": "jus orange carrefour",
    "choco": "chocolat",
    "choc":  "chocolat",
    "bf":    "beurre de cacahuètes",
    "pb":    "peanut butter",
    "ww":    "weight watchers",
    "mdd":   "marque de distributeur",
    "bio":   "biologique",
    "lait ec": "lait écrémé",
    "s. entier": "lait entier",
    "jambfc":  "jambon blanc",
    "st moret": "saint moret",
    "fjm":   "fjord",
    "activia": "activia danone",
    "prince": "prince lu",
    "pim":   "pim's",
    "bn":    "bn biscuit",
    "kiri":  "kiri fromage",
    "vach":  "vache qui rit",
    "vqr":   "vache qui rit",
    "miel pop": "honey pops",
    "choco pops": "choco pops kelloggs",
    "frosties": "frosties kelloggs",
    "spéci": "spécial k",
    "speck": "spécial k",
    "sk":    "special k",
    "nutella": "nutella ferrero",
    "noc":   "nocilla",
    "lo":    "light",
    "0%":    "0% matière grasse",
    "mg":    "matière grasse",
}


def expand_abbreviations(query: str) -> str:
    """Remplace les abréviations connues par leur forme longue."""
    q = query.lower().strip()
   
    for abbr, expansion in sorted(ABBREVIATIONS.items(), key=lambda x: -len(x[0])):
        pattern = r"\b" + re.escape(abbr) + r"\b"
        q = re.sub(pattern, expansion, q, flags=re.IGNORECASE)
    return q


def build_query_variants(raw: str) -> list[str]:
    """
    Génère plusieurs variantes de la requête, du plus précis au plus large :
    1. Requête originale normalisée
    2. Avec expansion des abréviations
    3. Troncature 3 mots, 2 mots
    4. Chaque mot seul
    Permet de trouver même si l'utilisateur abrège ou écrit différemment.
    """
    cleaned = normalize_query(raw)
    expanded = expand_abbreviations(cleaned)

    variants = []

    for base in [cleaned, expanded]:
        words = [w for w in base.split() if len(w) > 2]
        variants.append(base)
        if len(words) > 3:
            variants.append(" ".join(words[:4]))
        if len(words) > 2:
            variants.append(" ".join(words[:3]))
        if len(words) > 1:
            variants.append(" ".join(words[:2]))
        for word in words:
            variants.append(word)

    seen = []
    for v in variants:
        v = v.strip()
        if v and v not in seen:
            seen.append(v)
    return seen


def search_products(query: str, max_results: int = 2, worldwide: bool = False, fuzzy: bool = False) -> list:
    """
    Recherche sur Open Food Facts.
    - Par défaut : langue fr.
    - worldwide=True : sans filtre de pays/langue.
    - fuzzy=True : search_simple=0 (recherche avancée, tolère les fautes et noms partiels).
    """
    try:
        params = {
            "search_terms": query,
            "search_simple": 0 if fuzzy else 1,
            "action": "process",
            "json": 1,
            "page_size": max_results,
            "fields": (
                "product_name,brands,nutriscore_grade,nova_group,"
                "nutriments,additives_tags,quantity,labels_tags,ingredients_text"
            ),
        }
        if not worldwide:
            params["lc"] = "fr"

        r = requests.get(f"{OFF_BASE_URL}/cgi/search.pl", params=params, headers=OFF_HEADERS, timeout=10)
        r.raise_for_status()
        products = r.json().get("products", [])[:max_results]
        return [p for p in products if p.get("product_name")]
    except Exception as e:
        logger.error(f"OpenFoodFacts error: {e}")
        return []


def smart_search(raw_query: str, max_results: int = 2) -> tuple[list, str]:
    """
    Recherche progressive en 4 passes :
    1. Variantes normalisées + abréviations expansées, mode simple, langue fr
    2. Même chose, worldwide
    3. Via fr.openfoodfacts.org (sous-domaine)
    4. Mode fuzzy (search_simple=0) sur les variantes principales — tolère les fautes/noms partiels
    """
    variants = build_query_variants(raw_query)

    for variant in variants:
        logger.info(f"[OFF pass 1 - fr] '{variant}'")
        results = search_products(variant, max_results, worldwide=False)
        if results:
            return results, variant

    for variant in variants:
        logger.info(f"[OFF pass 2 - worldwide] '{variant}'")
        results = search_products(variant, max_results, worldwide=True)
        if results:
            return results, variant

    for variant in variants:
        try:
            logger.info(f"[OFF pass 3 - fr subdomain] '{variant}'")
            r = requests.get(
                "https://fr.openfoodfacts.org/cgi/search.pl",
                params={
                    "search_terms": variant,
                    "search_simple": 1,
                    "action": "process",
                    "json": 1,
                    "page_size": max_results,
                    "fields": "product_name,brands,nutriscore_grade,nova_group,nutriments,additives_tags,quantity,labels_tags,ingredients_text",
                },
                headers=OFF_HEADERS,
                timeout=10,
            )
            r.raise_for_status()
            products = [p for p in r.json().get("products", []) if p.get("product_name")]
            if products:
                return products[:max_results], variant
        except Exception as e:
            logger.error(f"OFF pass 3 error: {e}")

    for variant in variants[:4]:
        logger.info(f"[OFF pass 4 - fuzzy worldwide] '{variant}'")
        results = search_products(variant, max_results, worldwide=True, fuzzy=True)
        if results:
            return results, f"{variant} (fuzzy)"

    return [], raw_query


def format_product(product: dict) -> str:
    if not product:
        return ""

    name     = product.get("product_name") or "Nom inconnu"
    brand    = product.get("brands") or "Marque inconnue"
    quantity = product.get("quantity") or "N/A"
    ns_grade = (product.get("nutriscore_grade") or "n/a").lower()
    ns_label = NUTRISCORE_EMOJI.get(ns_grade, "❓ N/A")
    nova     = product.get("nova_group") or "N/A"

    n = product.get("nutriments", {})

    labels_raw = product.get("labels_tags", [])
    bio = "🌿 BIO" if any("organic" in l or "bio" in l for l in labels_raw) else ""

    additives_raw = product.get("additives_tags", [])
    additives_str = ", ".join(
        f"{a.replace('en:', '').upper()} {ADDITIVE_RISK.get(a, '')}".strip()
        for a in additives_raw[:6]
    ) if additives_raw else "Aucun additif détecté ✅"

    ingredients = product.get("ingredients_text") or "Non disponibles"
    if len(ingredients) > 200:
        ingredients = ingredients[:200] + "..."

    return (
        f"Produit : {name} ({brand}) {bio} — {quantity}\n"
        f"Nutri-Score : {ns_label} | NOVA (transformation) : {nova}/4\n"
        f"Calories : {n.get('energy-kcal_100g', 'N/A')} kcal/100g\n"
        f"Protéines : {n.get('proteins_100g', 'N/A')}g | "
        f"Glucides : {n.get('carbohydrates_100g', 'N/A')}g "
        f"(dont sucres : {n.get('sugars_100g', 'N/A')}g)\n"
        f"Lipides : {n.get('fat_100g', 'N/A')}g "
        f"(dont saturés : {n.get('saturated-fat_100g', 'N/A')}g) | "
        f"Sel : {n.get('salt_100g', 'N/A')}g\n"
        f"Additifs : {additives_str}\n"
        f"Ingrédients : {ingredients}"
    )

MEAL_KEYWORDS = [
    r"\bje mange\b", r"\bj.ai mangé\b", r"\bje vais manger\b",
    r"\brepas\b", r"\bassiette\b", r"\bcombien de calorie", r"\bcalories?\b",
    r"\bplat\b", r"\bdîner\b", r"\bdéjeuner\b", r"\bpetit.déj", r"\bsnack\b",
]

MEAL_INGREDIENT_STOPWORDS = {
    "je", "vais", "mange", "un", "une", "des", "du", "de", "la", "le", "les",
    "avec", "et", "ou", "plus", "aussi", "combien", "calorie", "calories",
    "kcal", "etc", "gros", "gros", "énorme", "petit", "grand", "plein",
    "complet", "complète", "bon", "bonne", "mange", "manger", "repas",
    "assiette", "vraiment", "beaucoup", "environ", "cela", "tout",
}

def is_meal_query(text: str) -> bool:
    text_lower = text.lower()
    return any(re.search(kw, text_lower) for kw in MEAL_KEYWORDS)


def extract_meal_ingredients(text: str) -> list[str]:
    """
    Extrait les ingrédients clés d'une question libre sur un repas.
    Ex : "couscous complet merguez yaourt" → ["couscous", "merguez", "yaourt"]
    """
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    words = cleaned.split()
    ingredients = [w for w in words if len(w) > 3 and w not in MEAL_INGREDIENT_STOPWORDS]
    
    seen = []
    for w in ingredients:
        if w not in seen:
            seen.append(w)
    return seen[:6]


def get_off_context_meal(text: str) -> str:
    """
    Pour les questions de repas libres : cherche chaque ingrédient
    séparément sur OFF et construit un contexte multi-produits.
    """
    ingredients = extract_meal_ingredients(text)
    if not ingredients:
        return ""

    parts = []
    for ingredient in ingredients:
        products = search_products(ingredient, max_results=1)
        if products:
            parts.append(f"=== {ingredient.upper()} ===\n{format_product(products[0])}")

    return "\n\n".join(parts) if parts else ""


def get_off_context_single(query: str) -> str:
    products = search_products(query, max_results=2)
    if not products:
        return ""
    parts = [format_product(p) for p in products if p.get("product_name")]
    return "\n---\n".join(parts) if parts else ""


def get_off_context_comparison(product_a: str, product_b: str) -> str:
    ctx_a = get_off_context_single(product_a)
    ctx_b = get_off_context_single(product_b)

    result = ""
    if ctx_a:
        result += f"=== DONNÉES POUR : {product_a} ===\n{ctx_a}\n\n"
    if ctx_b:
        result += f"=== DONNÉES POUR : {product_b} ===\n{ctx_b}\n"
    return result.strip()


def ask_lmstudio(user_input: str, history: list, off_context: str = "") -> str | None:
    try:
        from openai import OpenAI
        client = OpenAI(base_url=LMSTUDIO_URL, api_key="lm-studio")

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(history[-10:])

        if off_context:
            full_input = (
                f"{user_input}\n\n"
                f"[📦 Données Open Food Facts récupérées automatiquement :]\n"
                f"{off_context}"
            )
        else:
            full_input = user_input

        messages.append({"role": "user", "content": full_input})

        response = client.chat.completions.create(
            model="local-model",
            messages=messages,
            temperature=0.6,
            max_tokens=800,
        )
        return response.choices[0].message.content.strip()
    except Exception as error:
        logger.warning(f"LMStudio inaccessible : {error}")
        return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["history"] = []
    await update.message.reply_text(
        "👋 Bonjour ! Je suis *NutriBot* 🥗, votre expert nutrition IA pour vos courses.\n\n"
        "Je connais les produits de *Super U, Carrefour, Lidl, Leclerc, Intermarché, Aldi* et plus encore !\n\n"
        "📌 *Exemples de questions :*\n"
        "• _« Je suis au Super U, j'hésite entre le fromage blanc BIO Vrai et la Marque U, lequel est le plus healthy ? »_\n"
        "• _« Compare le Nutella et la pâte à tartiner Leclerc »_\n"
        "• _« Analyse le jambon Fleury Michon »_\n\n"
        "📋 *Commandes disponibles :*\n"
        "• `/nutri <produit>` — fiche nutritionnelle Open Food Facts\n"
        "• `/comparer <produit A> vs <produit B>` — comparaison directe\n"
        "• `/reset` — réinitialiser la conversation\n"
        "• `/ping` — tester la connexion\n\n"
        "💬 Ou écrivez directement votre question !",
        parse_mode="Markdown",
    )


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 pong — NutriBot est en ligne !")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["history"] = []
    await update.message.reply_text("🔄 Conversation réinitialisée. Nouvelle session démarrée !")


async def nutri_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Usage : `/nutri <produit>`\nEx : `/nutri fromage blanc vrai bio`",
            parse_mode="Markdown",
        )
        return

    raw_query = " ".join(context.args)
    await update.message.chat.send_action("typing")

    products, used_variant = smart_search(raw_query)

    if not products:
        await update.message.reply_text(
            f"😕 Aucun résultat pour *{raw_query}*. "
            f"Essayez avec le nom de la marque seul (ex : `/nutri vrai`, `/nutri danone`).",
            parse_mode="Markdown",
        )
        return

    parts = [format_product(p) for p in products if p.get("product_name")]
    off_context = "\n---\n".join(parts)

    header = f"📦 *Résultats pour « {raw_query} »*"
    if used_variant != normalize_query(raw_query):
        header += f"\n_Recherche effectuée avec : « {used_variant} »_"

    await update.message.reply_text(
        f"{header}\n\n```\n{off_context}\n```",
        parse_mode="Markdown",
    )


async def comparer_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Usage : `/comparer <produit A> vs <produit B>`\n"
            "Ex : `/comparer Nutella vs pâte à tartiner Carrefour`",
            parse_mode="Markdown",
        )
        return

    full_query = " ".join(context.args)
    parts = re.split(r"\s+vs\s+|\s+ou\s+|\s+et\s+", full_query, flags=re.IGNORECASE, maxsplit=1)

    if len(parts) < 2:
        await update.message.reply_text(
            "⚠️ Séparez les deux produits avec *vs*, *ou* ou *et*.\n"
            "Ex : `/comparer Fromage blanc Vrai vs Fromage blanc Marque U`",
            parse_mode="Markdown",
        )
        return

    product_a, product_b = parts[0].strip(), parts[1].strip()
    await update.message.chat.send_action("typing")

    await update.message.reply_text(
        f"🔎 Recherche en cours pour :\n• *{product_a}*\n• *{product_b}*\n\n_Patientez..._",
        parse_mode="Markdown",
    )

    off_context = get_off_context_comparison(product_a, product_b)
    history = context.user_data.setdefault("history", [])

    user_input = f"Compare ces deux produits et dis-moi lequel est le plus healthy : {product_a} vs {product_b}"
    reply = ask_lmstudio(user_input, history, off_context)

    if not reply:
        reply = (
            "⚠️ *Service IA Hors Ligne*\n\n"
            "Démarrez LMStudio (Local Server, port 1234) et rechargez.\n"
        )

    history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": reply})
    if len(history) > 20:
        context.user_data["history"] = history[-20:]

    await update.message.reply_text(reply, parse_mode="Markdown")


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    history = context.user_data.setdefault("history", [])

    await update.message.chat.send_action("typing")

    market = extract_supermarket(user_message)
    market_info = f" (contexte : {market})" if market else ""

    raw_cards = ""  

    if is_comparison_query(user_message):
        products = extract_products_from_message(user_message)
        logger.info(f"Comparaison détectée{market_info}. Produits extraits : {products}")

        if len(products) >= 2:
            off_context = get_off_context_comparison(products[0], products[1])
        else:
            off_context = get_off_context_single(user_message[:80])

    elif is_meal_query(user_message):
        logger.info(f"Question repas/calories détectée{market_info}.")
        off_context = get_off_context_meal(user_message)
        raw_cards = off_context  

    else:
        logger.info(f"Analyse simple détectée{market_info}.")
        off_context = get_off_context_single(user_message[:80])

    reply = ask_lmstudio(user_message, history, off_context)

    if not reply:
        reply = (
            "⚠️ *Service IA Hors Ligne*\n\n"
            "Démarrez LMStudio (Local Server, port 1234).\n"
            f"_Votre message :_ \"{user_message}\""
        )

    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": reply})
    if len(history) > 20:
        context.user_data["history"] = history[-20:]

    await update.message.reply_text(reply, parse_mode="Markdown")

    
    if raw_cards:
        await update.message.reply_text(
            f"📋 *Fiches nutritionnelles des ingrédients détectés :*\n\n```\n{raw_cards}\n```",
            parse_mode="Markdown",
        )


async def testapi_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /testapi — diagnostique la connexion à Open Food Facts.
    Teste 3 requêtes de référence et affiche les résultats.
    """
    await update.message.chat.send_action("typing")
    tests = [
        ("danone", False),
        ("nutella", False),
        ("gerble", True),
    ]
    lines = ["🔧 *Diagnostic Open Food Facts*\n"]
    for term, worldwide in tests:
        try:
            results = search_products(term, max_results=1, worldwide=worldwide)
            mode = "worldwide" if worldwide else "fr"
            if results:
                name = results[0].get("product_name", "?")[:40]
                lines.append(f"✅ `{term}` ({mode}) → {name}")
            else:
                lines.append(f"❌ `{term}` ({mode}) → aucun résultat")
        except Exception as e:
            lines.append(f"💥 `{term}` → erreur : {e}")

    lines.append("\n_Si tous les tests échouent, vérifiez votre connexion internet._")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


def main():
    logger.info("🚀 Démarrage NutriBot...")
    logger.info(f"🤖 LMStudio : {LMSTUDIO_URL}")
    logger.info(f"🥗 Open Food Facts : {OFF_BASE_URL}")

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start",    start))
    application.add_handler(CommandHandler("ping",     ping))
    application.add_handler(CommandHandler("help",     help_cmd))
    application.add_handler(CommandHandler("reset",    reset))
    application.add_handler(CommandHandler("nutri",    nutri_cmd))
    application.add_handler(CommandHandler("comparer", comparer_cmd))
    application.add_handler(CommandHandler("testapi",  testapi_cmd))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    logger.info("✅ NutriBot prêt ! En attente de messages...")
    application.run_polling()


if __name__ == "__main__":
    main()