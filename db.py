import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
# IMPORTANT : Ici on utilise la clé SERVICE_ROLE (Master) récupérée dans Supabase
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Erreur : SUPABASE_URL ou SUPABASE_KEY manquant dans l'environnement.")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def already_analyzed(ticker):
    """Vérifie directement dans Supabase si le ticker existe déjà dans ipo_analyses.
    Remplace l'ancien système de fichier texte local : plus fiable, plus de risque
    de désync entre le repo Git et la vraie source de vérité."""
    try:
        result = (
            supabase.table("ipo_analyses")
            .select("ticker")
            .eq("ticker", ticker.upper())
            .limit(1)
            .execute()
        )
        return len(result.data) > 0
    except Exception as e:
        print(f"⚠️ Erreur lors de la vérification de dédup pour {ticker} : {e}")
        # En cas de doute (panne réseau, etc.), on considère que ce n'est pas encore analysé
        # plutôt que de bloquer silencieusement l'agent.
        return False


def save_analysis(ticker, company_name, exchange, sec_filing_url, ai_report, risk_short, risk_long, ipo_date, status="À venir", market="US", country="USA", price_range="-", valuation="-", amount_raised="-"):
    """Enregistre l'analyse complète dans la table ipo_analyses de Supabase"""

    data = {
        "ticker": ticker.upper(),
        "company_name": company_name,
        "sec_filing_url": sec_filing_url,
        "ai_report": ai_report,
        "risk_score_short_term": risk_short,
        "risk_score_long_term": risk_long,
        "ipo_date": ipo_date,
        "status": status,
        "market": market,
        "country": country,
        "price_range": price_range,
        "valuation": valuation,
        "amount_raised": amount_raised
    }

    try:
        supabase.table("ipo_analyses").insert(data).execute()
        print(f"✅ [Supabase] Analyse de {ticker} insérée avec succès.")
    except Exception as e:
        print(f"❌ Erreur lors de l'insertion Supabase pour {ticker} : {e}")