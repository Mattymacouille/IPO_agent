import os
from datetime import datetime, timedelta
import requests
import html2text
from dotenv import load_dotenv
from anthropic import Anthropic

# Charger les variables d'environnement
load_dotenv()
FINNHUB_KEY = os.getenv("FINNHUB_API_KEY")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")

SEC_HEADERS = {"User-Agent": "MonAgentIA monemail@exemple.com"}
DB_FILE = "analysed_ipos.txt"  # Fichier qui sert de mémoire à l'agent

if ANTHROPIC_KEY:
    anthropic_client = Anthropic(api_key=ANTHROPIC_KEY)
else:
    print("⚠️ Attention : ANTHROPIC_API_KEY manquante.")
    anthropic_client = None

def load_analysed_tickers():
    """Charge la liste des tickers déjà analysés par le passé"""
    if not os.path.exists(DB_FILE):
        return set()
    with open(DB_FILE, "r", encoding="utf-8") as f:
        # On nettoie les espaces et on met tout en majuscules
        return set(line.strip().upper() for line in f if line.strip())

def save_analysed_ticker(ticker):
    """Sauvegarde un ticker dans le fichier pour ne plus le réanalyser"""
    with open(DB_FILE, "a", encoding="utf-8") as f:
        f.write(f"{ticker.upper()}\n")

def get_sec_cik(ticker):
    url = "https://www.sec.gov/files/company_tickers.json"
    try:
        response = requests.get(url, headers=SEC_HEADERS, timeout=5)
        if response.status_code == 200:
            data = response.json()
            for item in data.values():
                if item["ticker"].upper() == ticker.upper():
                    return str(item["cik_str"]).zfill(10)
    except Exception:
        pass
    return None

def get_s1_document_url(cik):
    if not cik:
        return None
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    try:
        response = requests.get(url, headers=SEC_HEADERS, timeout=5)
        if response.status_code == 200:
            filings = response.json().get("filings", {}).get("recent", {})
            for i, form in enumerate(filings.get("form", [])):
                if form in ["S-1", "S-1/A", "F-1", "F-1/A"]:
                    accession_num = filings["accessionNumber"][i].replace("-", "")
                    primary_doc = filings["primaryDocument"][i]
                    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_num}/{primary_doc}"
    except Exception:
        pass
    return None

def analyze_document_with_claude(doc_url, company_name):
    if not anthropic_client:
        return "❌ Analyse impossible : Clé API Claude manquante."
        
    print(f"   🧠 Extraction du texte et transmission à Claude...")
    try:
        response = requests.get(doc_url, headers=SEC_HEADERS, timeout=15)
        response.raise_for_status()
        
        h = html2text.HTML2Text()
        h.ignore_links = True
        h.ignore_images = True
        raw_text = h.handle(response.text)[:200000] # Limité à ~35 pages pour le budget
        
        prompt_system = (
            "Tu es un analyste financier senior et un gestionnaire de risques cynique. "
            "Tu analyses un document d'IPO pour détecter les failles, dettes et risques de gouvernance. "
            "Ignore le marketing de la boîte. Reste factuel, froid et très critique."
        )
        
        prompt_user = f"""Voici un extrait du document d'introduction en bourse de l'entreprise {company_name}.
        Génère un rapport financier structuré :
        
        1. **Business Model Réel** (Comment ils font de l'argent concrètement, sans jargon).
        2. **Drapeaux Rouges & Pièges** (Cash burn, dettes, litiges, concentration de clients ou fondateurs intouchables).
        3. **Note de Risque Globale** (Sur une échelle de 1 à 10, où 10 est un risque maximum d'effondrement). Justifie la note en une phrase.
        
        Texte source :
        {raw_text}
        """
        
        # Correction modèle 2026 + augmentation max_tokens pour éviter les coupures
        message = anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000, 
            temperature=0.1,
            system=prompt_system,
            messages=[{"role": "user", "content": prompt_user}],
        )
        return message.content[0].text
        
    except Exception as e:
        return f"❌ Échec de l'analyse : {e}"

def run_ipo_agent():
    start_date = datetime.now().strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    
    url = "https://finnhub.io/api/v1/calendar/ipo"
    params = {"from": start_date, "to": end_date, "token": FINNHUB_KEY}
    
    print(f"🔄 [Lancement] Surveillance du marché du {start_date} au {end_date}...")
    
    # ÉTAPE EXCLUSION : Charger l'historique
    analysed_tickers = load_analysed_tickers()
    
    try:
        response = requests.get(url, params=params, timeout=10)
        ipo_list = response.json().get("ipoCalendar", [])
        
        if not ipo_list:
            print("📅 Aucune IPO détectée sur cette période.")
            return
            
        print(f"✨ {len(ipo_list)} entreprise(s) sur le radar.\n")
        
        for ipo in ipo_list:
            name = ipo.get("name", "Inconnu")
            ticker = ipo.get("symbol", "N/A").upper()
            exchange = ipo.get("exchange", "Inconnu")
            
            print(f"🏢 ÉVALUATION : {name} ({ticker}) | {exchange}")
            
            # FILTRE ANTIDOUBLON : Si déjà vu, on zappe direct
            if ticker in analysed_tickers:
                print(f"   ⏭️ Déjà analysé par le passé ({ticker}). On passe à la suite.")
                print("-" * 60)
                continue
            
            if "NYSE" in exchange or "NASDAQ" in exchange:
                cik = get_sec_cik(ticker)
                if cik:
                    doc_url = get_s1_document_url(cik)
                    if doc_url:
                        print(f"   📄 Document S-1 localisé : {doc_url}")
                        rapport = analyze_document_with_claude(doc_url, name)
                        print("\n" + "="*20 + " RAPPORT IA " + "="*20)
                        print(rapport)
                        print("="*52 + "\n")
                        
                        # SUCCÈS : On enregistre pour ne plus jamais payer pour cette boîte
                        save_analysed_ticker(ticker)
                    else:
                        print("   ❌ Document S-1 introuvable pour le moment.")
                else:
                    print("   ❌ Ticker non encore indexé par le registre SEC global.")
            else:
                print("   🌍 Marché International - Ignoré pour cette version.")
            print("-" * 60)
            
    except Exception as e:
        print(f"❌ Erreur générale de l'agent : {e}")

if __name__ == "__main__":
    run_ipo_agent()