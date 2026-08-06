import os
from datetime import datetime, timedelta
import requests
import html2text
from dotenv import load_dotenv
from anthropic import Anthropic
from db import already_analyzed, save_analysis
import re
import json

load_dotenv()
FINNHUB_KEY = os.getenv("FINNHUB_API_KEY")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")

SEC_HEADERS = {"User-Agent": "MonAgentIA monemail@exemple.com"}

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

    print("Extraction du texte et transmission à Claude...")
    try:
        response = requests.get(doc_url, headers=SEC_HEADERS, timeout=15)
        response.raise_for_status()

        h = html2text.HTML2Text()
        h.ignore_links = True
        h.ignore_images = True
        raw_text = h.handle(response.text)[:200000]

        # ------------------------------------------------------------------
        # PROMPT SYSTEM : grille d'analyse explicite, pas juste "sois critique"
        # Chaque axe correspond à un vrai point qu'un analyste IPO vérifie
        # systématiquement. Forcer une balise par axe évite que Claude en
        # zappe un sans que ça se voie dans un texte libre.
        # ------------------------------------------------------------------
        prompt_system = (
            "Tu es un analyste financier senior spécialisé en introductions en bourse (IPO). "
            "Tu appliques une grille d'analyse fixe et rigoureuse à chaque document S-1/F-1, sans exception. "
            "Reste factuel et froid. Ignore le langage marketing du prospectus. "
            "Si une information n'est pas trouvable dans le texte fourni, écris explicitement 'Non communiqué dans l'extrait' "
            "plutôt que d'inventer un chiffre ou une estimation.\n\n"

            "CONSIGNE TECHNIQUE IMPÉRATIVE :\n"
            "Tu dois TOUJOURS répondre en remplissant EXACTEMENT le bloc de balises suivant, dans cet ordre, "
            "avant tout autre texte. N'ajoute aucun texte en dehors des balises.\n\n"

            "<meta_data>\n"
            "<status>À venir</status>\n"
            "<market>NASDAQ</market>\n"
            "<country>USA</country>\n"
            "<price_range>Prix ou fourchette (ex: $18.00 - $21.00 ou 'Non fixé')</price_range>\n"
            "<valuation>Valorisation estimée (ex: $450M ou 'Inconnue')</valuation>\n"
            "<amount_raised>Montant levé visé (ex: $50M ou 'Inconnu')</amount_raised>\n"
            "</meta_data>\n\n"

            "[SCORE_CT: X/10]\n"
            "[SCORE_LT: Y/10]\n"
            "(X et Y sont des entiers 1-10, où 10 = confiance maximale / risque minimal)\n\n"

            "<business_model>Comment l'entreprise gagne concrètement de l'argent, marge brute si connue, "
            "rentable ou non, burn rate mensuel approximatif. 3-4 phrases max.</business_model>\n\n"

            "<burn_rate_runway>Cash disponible et burn rate mensuel si communiqués, et estimation du runway "
            "(nombre de mois avant manque de liquidités au rythme actuel). 'Non communiqué' si absent du texte.</burn_rate_runway>\n\n"

            "<use_of_proceeds>À quoi va servir l'argent levé : remboursement de dette (signal négatif) "
            "vs investissement en croissance (signal positif). 2-3 phrases.</use_of_proceeds>\n\n"

            "<lockup_period>Durée de la période de lock-up des insiders si mentionnée (ex: '180 jours'). "
            "'Non communiqué' si absent.</lockup_period>\n\n"

            "<governance_notes>Structure à droits de vote différenciés (dual-class) oui/non, part détenue "
            "par les fondateurs et par les VC/PE qui pourraient vendre à l'IPO. 2-3 phrases.</governance_notes>\n\n"

            "<competitive_moat>Avantage compétitif réellement défendable (brevets, effet réseau, coûts de "
            "changement) ou absence de moat clair. 2-3 phrases, sois sceptique par défaut.</competitive_moat>\n\n"

            "<comparable_valuation>Le prix demandé semble-t-il cohérent avec des entreprises comparables déjà "
            "cotées (multiple de revenu/EBITDA si calculable) ? 'Non évaluable avec les données disponibles' si "
            "impossible à juger.</comparable_valuation>\n\n"

            "<going_concern>oui ou non — le document mentionne-t-il un doute explicite sur la continuité "
            "d'exploitation (going concern) ? C'est le signal le plus grave possible, ne jamais le manquer.</going_concern>\n\n"

            "<strengths>\n"
            "- Point fort 1\n"
            "- Point fort 2\n"
            "- Point fort 3 (2 à 4 points, un par ligne, commence chaque ligne par '- ')\n"
            "</strengths>\n\n"

            "<weaknesses>\n"
            "- Point faible 1\n"
            "- Point faible 2 (2 à 4 points, un par ligne, commence chaque ligne par '- ')\n"
            "</weaknesses>\n\n"

            "<red_flags>\n"
            "- Signal d'alerte critique 1\n"
            "- Signal d'alerte critique 2 (0 à 3 points maximum, uniquement les plus graves, "
            "liste vide avec juste '- Aucun signal critique identifié' si rien de grave)\n"
            "</red_flags>"
        )

        prompt_user = f"""Voici un extrait du document d'introduction en bourse de l'entreprise {company_name}.

Applique la grille d'analyse complète telle que définie dans tes instructions système, en remplissant
chaque balise avec précision à partir du texte source ci-dessous. Ne développe pas au-delà des limites
de longueur indiquées pour chaque section.

Texte source :
{raw_text}
"""

        message = anthropic_client.messages.create(
            model="claude-sonnet-5",
            max_tokens=6000,
            system=prompt_system,
            messages=[{"role": "user", "content": prompt_user}],
        )
        return message.content[0].text

    except Exception as e:
        return f"Échec de l'analyse : {e}"


def extract_tag(tag_name, text, default="-"):
    match = re.search(f"<{tag_name}>(.*?)</{tag_name}>", text, re.DOTALL)
    return match.group(1).strip() if match else default


def extract_list(tag_name, text):
    """Extrait une liste à puces ('- point') dans une balise et la renvoie comme liste Python,
    prête à être stockée en JSONB dans Supabase."""
    block = extract_tag(tag_name, text, default="")
    if not block:
        return []
    items = re.findall(r"-\s*(.+)", block)
    return [item.strip() for item in items if item.strip()]


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

        print(f"{len(ipo_list)} entreprise(s) sur le radar.\n")

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
                        print("\n" + "=" * 20 + " RAPPORT IA " + "=" * 20)
                        print(rapport)
                        print("=" * 52 + "\n")

                        # --- Métadonnées simples ---
                        market = extract_tag("market", rapport, exchange)
                        country = extract_tag("country", rapport, "USA")
                        price_range = extract_tag("price_range", rapport, "-")
                        valuation = extract_tag("valuation", rapport, "-")
                        amount_raised = extract_tag("amount_raised", rapport, "-")

                        # --- Grille d'analyse structurée ---
                        business_model = extract_tag("business_model", rapport, "Non communiqué")
                        burn_rate_runway = extract_tag("burn_rate_runway", rapport, "Non communiqué")
                        use_of_proceeds = extract_tag("use_of_proceeds", rapport, "Non communiqué")
                        lockup_period = extract_tag("lockup_period", rapport, "Non communiqué")
                        governance_notes = extract_tag("governance_notes", rapport, "Non communiqué")
                        competitive_moat = extract_tag("competitive_moat", rapport, "Non communiqué")
                        comparable_valuation = extract_tag("comparable_valuation", rapport, "Non évaluable")
                        going_concern_raw = extract_tag("going_concern", rapport, "non").lower()
                        has_going_concern_doubt = going_concern_raw.startswith("oui")

                        strengths = extract_list("strengths", rapport)
                        weaknesses = extract_list("weaknesses", rapport)
                        red_flags = extract_list("red_flags", rapport)

                        if has_going_concern_doubt:
                            print("⚠️  ALERTE GOING CONCERN — doute explicite sur la continuité d'exploitation.")

                        # --- Scores de risque ---
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

                        if risk_short is None:
                            risk_short = 5
                        if risk_long is None:
                            risk_long = 5

                        print(f"Risque CT: {risk_short}/10 | Risque LT: {risk_long}/10")

                        # Rapport texte "brut" nettoyé (gardé pour compatibilité / lecture libre)
                        clean_report = re.sub(r"<meta_data>.*?</meta_data>", "", rapport, flags=re.DOTALL).strip()

                        save_analysis(
                            ticker=ticker,
                            company_name=name,
                            exchange=exchange,
                            sec_filing_url=doc_url,
                            ai_report=clean_report,
                            risk_short=risk_short,
                            risk_long=risk_long,
                            ipo_date=date_listing,
                            status="À venir",
                            market=market,
                            country=country,
                            price_range=price_range,
                            valuation=valuation,
                            amount_raised=amount_raised,
                            business_model=business_model,
                            burn_rate_runway=burn_rate_runway,
                            use_of_proceeds=use_of_proceeds,
                            lockup_period=lockup_period,
                            governance_notes=governance_notes,
                            competitive_moat=competitive_moat,
                            comparable_valuation=comparable_valuation,
                            has_going_concern_doubt=has_going_concern_doubt,
                            strengths=strengths,
                            weaknesses=weaknesses,
                            red_flags=red_flags,
                        )
                    else:
                        print("Document S-1 introuvable pour le moment.")
                else:
                    print("Ticker non encore indexé par le registre SEC global.")
            else:
                print("Marché International - Ignoré pour cette version.")
            print("-" * 60)

    except Exception as e:
        print(f"Erreur générale de l'agent : {e}")


if __name__ == "__main__":
    run_ipo_agent()