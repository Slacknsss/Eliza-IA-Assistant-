# B-AIA-210-PAR-2-1-eliza-6 — NutriBot

NutriBot est un assistant nutrition IA pour la grande distribution française.  
Il analyse des produits alimentaires via Open Food Facts et répond aux questions nutritionnelles via un LLM local (LMStudio).

Deux interfaces sont disponibles :
- Un **bot Telegram** (`bot.py`)
- Une **interface web** avec une API Flask (`app.py` + `site/index_1.html`)

---

## Prérequis

- Python 3.10+
- [LMStudio](https://lmstudio.ai/) avec un modèle chargé et le serveur local démarré (port 1234)
- Un bot Telegram créé via [@BotFather](https://t.me/BotFather)

---

## Installation

```bash
git clone git@github.com:EpitechBachelorPromo2028/B-AIA-210-PAR-2-1-eliza-6.git
cd B-AIA-210-PAR-2-1-eliza-6/bot
pip install -r requirements.txt
```

Créer un fichier `.env` dans `bot/` :

```env
TELEGRAM_TOKEN=ton_token_telegram
LMSTUDIO_URL=http://127.0.0.1:1234/v1
OFF_BASE_URL=https://world.openfoodfacts.org
```

---

## Lancement

**Bot Telegram :**
```bash
python bot.py
```

**Interface web (API Flask) :**
```bash
python app.py
```
Accessible sur `http://localhost:8080`

---

## Fonctionnalités

- Analyse nutritionnelle d'un produit (Nutri-Score, NOVA, additifs, macros)
- Comparaison de deux produits
- Estimation calorique d'un repas (bot Telegram)
- Recherche intelligente sur Open Food Facts (variantes, abréviations, fuzzy search)
- Historique de conversation par session

**Commandes Telegram disponibles :**

| Commande | Description |
|---|---|
| `/start` | Démarrer le bot |
| `/nutri <produit>` | Fiche nutritionnelle |
| `/comparer <A> vs <B>` | Comparer deux produits |
| `/reset` | Réinitialiser la conversation |
| `/ping` | Tester la connexion |
| `/testapi` | Diagnostic Open Food Facts |

---

## Structure du projet

```
├── bot/
│   ├── app.py           # API Flask + interface web
│   ├── bot.py           # Bot Telegram
│   └── requirements.txt
├── site/
│   └── index_1.html     # Frontend web
└── bootstrap/
    └── bruno/           # Analyse de la chaîne de valeur
```

---

## Données

Les données nutritionnelles proviennent de [Open Food Facts](https://world.openfoodfacts.org), base de données ouverte et collaborative.
