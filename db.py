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
DB_FILE = "analysed_ipos.txt"

def already_analyzed(ticker):
    """Vérifie dans la mémoire locale (txt) si le ticker a déjà été traité"""
    if not os.path.exists(DB_FILE):
        return False
    with open(DB_FILE, "r") as f:
        analyzed = f.read().splitlines()
    return ticker.upper() in analyzed

def save_analysis(ticker, company_name, exchange, sec_filing_url, ai_report, risk_short, risk_long, ipo_date, status="À venir", market="US", country="USA", price_range="-", valuation="-", amount_raised="-"):
    """Enregistre l'analyse complète dans la table ipo_analyses de Supabase"""
    
    # 1. On prépare le dictionnaire avec les exacts noms de colonnes de ta BDD
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
        # 2. Insertion dans Supabase
        supabase.table("ipo_analyses").insert(data).execute()
        print(f"✅ [Supabase] Analyse de {ticker} insérée avec succès.")
        
        # 3. Sauvegarde dans la mémoire locale (analysed_ipos.txt) pour ne pas la refaire demain
        with open(DB_FILE, "a") as f:
            f.write(f"{ticker.upper()}\n")
            
    except Exception as e:
        print(f"❌ Erreur lors de l'insertion Supabase pour {ticker} : {e}")