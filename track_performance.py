"""
Capture quotidienne des prix pour le suivi de performance post-IPO (J+1/J+7/J+30/J+90).

Utilise l'endpoint /quote de Finnhub (gratuit), pas /stock/candle (passé payant).
À exécuter une fois par jour via GitHub Actions, en plus (et séparément) de main.py.
"""
import os
import requests
from datetime import date, timedelta
from dotenv import load_dotenv
from db import supabase

load_dotenv()
FINNHUB_KEY = os.getenv("FINNHUB_API_KEY")

# Fenêtre de suivi : on capture le prix des IPO listées il y a moins de ~95 jours
# (marge de sécurité au-delà de J+90 pour ne rater aucun point de mesure)
TRACKING_WINDOW_DAYS = 95


def get_tracked_tickers():
    """Récupère les tickers dont l'IPO date de moins de 95 jours, donc encore utiles à suivre."""
    cutoff = (date.today() - timedelta(days=TRACKING_WINDOW_DAYS)).isoformat()
    result = (
        supabase.table("ipo_analyses")
        .select("ticker, ipo_date")
        .gte("ipo_date", cutoff)
        .execute()
    )
    return result.data or []


def get_quote(ticker):
    """Appelle /quote (gratuit) et renvoie le prix courant (champ 'c')."""
    url = "https://finnhub.io/api/v1/quote"
    params = {"symbol": ticker, "token": FINNHUB_KEY}
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        price = data.get("c")
        # Finnhub renvoie 0 quand le ticker est inconnu/pas encore de données —
        # on l'ignore pour ne pas polluer l'historique avec des zéros
        if price and price > 0:
            return price
    except Exception as e:
        print(f"⚠️ Erreur quote pour {ticker} : {e}")
    return None


def save_price_snapshot(ticker, price):
    """Enregistre le prix du jour. Upsert pour éviter les doublons si le job tourne 2x le même jour."""
    today = date.today().isoformat()
    try:
        supabase.table("price_history").upsert(
            {"ticker": ticker, "price": price, "captured_at": today},
            on_conflict="ticker,captured_at"
        ).execute()
        print(f"✅ {ticker} : {price} capturé pour le {today}")
    except Exception as e:
        print(f"❌ Erreur d'enregistrement pour {ticker} : {e}")


def run_price_tracking():
    tickers = get_tracked_tickers()
    if not tickers:
        print("Aucun ticker à suivre pour le moment.")
        return

    print(f"Suivi de {len(tickers)} ticker(s)...\n")
    for row in tickers:
        ticker = row["ticker"]
        price = get_quote(ticker)
        if price:
            save_price_snapshot(ticker, price)
        else:
            print(f"⏭️  {ticker} : pas de prix disponible (pas encore coté ou hors marché ?)")


if __name__ == "__main__":
    run_price_tracking()