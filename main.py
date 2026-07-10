import os
from datetime import datetime, timedelta
import requests
import html2text
from dotenv import load_dotenv
from anthropic import Anthropic
from db import already_analyzed, save_analysis
import re    # Conforme pour le parsing regex
import json  # Conforme pour décoder le JSON

# Charger les variables d'environnement
load_dotenv()
FINNHUB_KEY = os.getenv("FINNHUB_API_KEY")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")

SEC_HEADERS = {"User-Agent": "MonAgentIA monemail@exemple.com"}
DB_FILE = "analysed_ipos.txt"  # Fichier qui sert de mémoire à l'agent

if ANTHROPIC_KEY:
    anthropic_client = Anthropic(api_key=ANTHROPIC_KEY)
else:
    print("Attention : ANTHROPIC_API_KEY manquante.")
    anthropic_client = None


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
        return "Analyse impossible : Clé API Claude manquante."
        
    print(f"Extraction du texte et transmission à Claude...")
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
            "Ignore le marketing. Reste factuel, froid et très critique. "
            "SOIS SYNTHÉTIQUE : va droit au but, limite-toi aux 3 ou 4 drapeaux rouges les plus destructeurs ou alors si t'estimes qu'ils sont importants donne les moi tous mais ne developpe pas. "
            "Ton rapport complet ne doit pas dépasser 800 mots pour tenir entièrement dans la réponse.\n\n"
            
            "CONSIGNE TECHNIQUE IMPÉRATIVE :\n"
            "Avant de commencer ton rapport, tu dois TOUJOURS inclure le bloc de métadonnées suivant tout en haut de ta réponse. "
            "Remplis chaque balise avec les données trouvées dans le texte :\n"
            "<meta_data>\n"
            "<status>À venir</status>\n"
            "<market>NASDAQ</market>\n"
            "<country>USA</country>\n"
            "<price_range>Prix ou fourchette (ex: $18.00 - $21.00 ou 'Non fixé')</price_range>\n"
            "<valuation>Valorisation estimée (ex: $450M ou 'Inconnue')</valuation>\n"
            "<amount_raised>Montant levé visé (ex: $50M ou 'Inconnu')</amount_raised>\n"
            "</meta_data>"
        )
        prompt_user = f"""Voici un extrait du document d'introduction en bourse de l'entreprise {company_name}.

            CONSIGNE CRITIQUE : Juste après la balise </meta_data> fermée, tu dois IMPÉRATIVEMENT commencer ton rapport par ces deux lignes exactes :
            [SCORE_CT: X/10]
            [SCORE_LT: Y/10]
            (Remplace X et Y par des nombres entiers entre 1 et 10, puis saute une ligne et commence ton rapport).

            Génère un rapport financier structuré et TRÈS SYNTHÉTIQUE (maximum 600 mots) :
            1. **Business Model Réel** (En 4-5 phrases max).
            2. **Drapeaux Rouges & Pièges** (Limite-toi strictement aux 3 points les plus critiques, sans t'étaler).
            3. **Analyse Temporelle** (Une courte synthèse pour le Court Terme et le Long Terme).

            Texte source :
            {raw_text}
            """
        
        message = anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000, 
            temperature=0.1,
            system=prompt_system,
            messages=[{"role": "user", "content": prompt_user}],
        )
        return message.content[0].text
        
    except Exception as e:
        return f"Échec de l'analyse : {e}"

def run_ipo_agent():
    start_date = datetime.now().strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    
    url = "https://finnhub.io/api/v1/calendar/ipo"
    params = {"from": start_date, "to": end_date, "token": FINNHUB_KEY}
    
    print(f"[Lancement] Surveillance du marché du {start_date} au {end_date}...")
    
    try:
        response = requests.get(url, params=params, timeout=10)
        ipo_list = response.json().get("ipoCalendar", [])
        
        if not ipo_list:
            print("Aucune IPO détectée sur cette période.")
            return
            
        print(f"✨ {len(ipo_list)} entreprise(s) sur le radar.\n")
        
        for ipo in ipo_list:
            name = ipo.get("name", "Inconnu")
            ticker = ipo.get("symbol", "N/A").upper()
            exchange = ipo.get("exchange", "Inconnu")
            date_listing = ipo.get("date", None) 
            
            print(f"ÉVALUATION : {name} ({ticker}) | {exchange} | Date : {date_listing}")
            
            if already_analyzed(ticker):
                print(f"Déjà analysé par le passé ({ticker}). On passe à la suite.")
                print("-" * 60)
                continue
            
            if "NYSE" in exchange or "NASDAQ" in exchange:
                cik = get_sec_cik(ticker)
                if cik:
                    doc_url = get_s1_document_url(cik)
                    if doc_url:
                        print(f"Document S-1 localisé : {doc_url}")
                        rapport = analyze_document_with_claude(doc_url, name)
                        print("\n" + "="*20 + " RAPPORT IA " + "="*20)
                        print(rapport)
                        print("="*52 + "\n")
                        
                        # --- ENTRACTION DES BALISES XML COMPORTANT LES COMPOSANTS ---
                        def extract_tag(tag_name, text, default="-"):
                            match = re.search(f"<{tag_name}>(.*?)</{tag_name}>", text, re.DOTALL)
                            return match.group(1).strip() if match else default

                        status = extract_tag("status", rapport, "À venir")
                        market = extract_tag("market", rapport, exchange)
                        country = extract_tag("country", rapport, "USA")
                        price_range = extract_tag("price_range", rapport, "-")
                        valuation = extract_tag("valuation", rapport, "-")
                        amount_raised = extract_tag("amount_raised", rapport, "-")

                        # --- PARSING DES NOTES & INVERSION POUR LE RISQUE ---
                        risk_short = None
                        risk_long = None

                        match_ct = re.search(r"\[SCORE_CT:\s*(\d+)/10\]", rapport, re.IGNORECASE)
                        match_lt = re.search(r"\[SCORE_LT:\s*(\d+)/10\]", rapport, re.IGNORECASE)

                        if match_ct:
                            score_brut_ct = int(match_ct.group(1))
                            risk_short = 10 - score_brut_ct
                            
                        if match_lt:
                            score_brut_lt = int(match_lt.group(1))
                            risk_long = 10 - score_brut_lt

                        if risk_short is not None and risk_long is not None:
                            print(f"🎯 Risques calculés -> Risque CT: {risk_short}/10 (Score: {score_brut_ct}), Risque LT: {risk_long}/10 (Score: {score_brut_lt})")
                        else:
                            print(f"⚠️ Notes partielles ou manquantes. Attribution de valeurs médianes de secours.")
                            risk_short = risk_short if risk_short is not None else 5
                            risk_long = risk_long if risk_long is not None else 5

                        # Nettoyage cosmétique complet : on efface tout le bloc <meta_data>...</meta_data> du texte final
                        clean_report = re.sub(r"<meta_data>.*?</meta_data>", "", rapport, flags=re.DOTALL).strip()
                        # --- FIN DU PARSING ---

                        # Enregistrement dans Supabase avec les nouveaux arguments
                        save_analysis(
                            ticker=ticker,
                            company_name=name,
                            exchange=exchange,
                            sec_filing_url=doc_url,
                            ai_report=clean_report,
                            risk_short=risk_short,
                            risk_long=risk_long,
                            ipo_date=date_listing,
                            status=status,
                            market=market,
                            country=country,
                            price_range=price_range,
                            valuation=valuation,
                            amount_raised=amount_raised
                        )
                    else:
                        print("Document S-1 introuvable pour le moment.")
                else:
                    print("Ticker non encore indexé par le registre SEC global.")
            else:
                print(" Marché International - Ignoré pour cette version.")
            print("-" * 60)
            
    except Exception as e:
        print(f"Erreur générale de l'agent : {e}")

if __name__ == "__main__":
    run_ipo_agent()