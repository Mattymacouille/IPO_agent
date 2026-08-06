"""
Script de test isolé pour valider le nouveau prompt structuré,
SANS écrire dans Supabase et SANS passer par already_analyzed.

Usage : python test_prompt_structure.py TICKER "Nom de l'entreprise"
Exemple : python test_prompt_structure.py CSQR "Csquare, Inc."
"""
import sys
from main import get_sec_cik, get_s1_document_url, analyze_document_with_claude, extract_tag, extract_list
import re

def test_ticker(ticker, company_name):
    print(f"--- Recherche du CIK pour {ticker} ---")
    cik = get_sec_cik(ticker)
    if not cik:
        print("Ticker non trouvé dans le registre SEC. Essaie un autre ticker déjà coté/S-1 déposé.")
        return

    print(f"CIK trouvé : {cik}")
    doc_url = get_s1_document_url(cik)
    if not doc_url:
        print("Aucun document S-1/F-1 trouvé pour ce ticker.")
        return

    print(f"Document localisé : {doc_url}")
    print("--- Envoi à Claude (peut prendre 10-20s) ---\n")

    rapport = analyze_document_with_claude(doc_url, company_name)

    print("=" * 60)
    print("RAPPORT BRUT RENVOYÉ PAR CLAUDE")
    print("=" * 60)
    print(rapport)
    print("=" * 60)

    print("\n--- VÉRIFICATION DU PARSING ---\n")
    fields = [
        "business_model", "burn_rate_runway", "use_of_proceeds", "lockup_period",
        "governance_notes", "competitive_moat", "comparable_valuation", "going_concern"
    ]
    for f in fields:
        val = extract_tag(f, rapport, "❌ NON TROUVÉ")
        print(f"{f} : {val[:150]}")

    print("\nstrengths  :", extract_list("strengths", rapport))
    print("weaknesses :", extract_list("weaknesses", rapport))
    print("red_flags  :", extract_list("red_flags", rapport))

    match_ct = re.search(r"\[SCORE_CT:\s*(\d+)/10\]", rapport, re.IGNORECASE)
    match_lt = re.search(r"\[SCORE_LT:\s*(\d+)/10\]", rapport, re.IGNORECASE)
    print("\nSCORE_CT trouvé :", match_ct.group(1) if match_ct else "❌ NON TROUVÉ")
    print("SCORE_LT trouvé :", match_lt.group(1) if match_lt else "❌ NON TROUVÉ")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print('Usage : python test_prompt_structure.py TICKER "Nom entreprise"')
        sys.exit(1)
    test_ticker(sys.argv[1], sys.argv[2])