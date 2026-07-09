import os
from supabase import create_client, Client

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_KEY"]
        _client = create_client(url, key)
    return _client


def already_analyzed(ticker: str) -> bool:
    """Remplace la lecture de analysed_ipos.txt"""
    client = get_client()
    result = client.table("ipo_analyses").select("ticker").eq("ticker", ticker.upper()).execute()
    return len(result.data) > 0


def save_analysis(
    ticker: str,
    company_name: str,
    exchange: str,
    sec_filing_url: str,
    ai_report: str,
    risk_short: int | None,
    risk_long: int | None,
) -> None:
    """Remplace l'écriture dans analysed_ipos.txt"""
    client = get_client()
    client.table("ipo_analyses").insert({
        "ticker": ticker.upper(),
        "company_name": company_name,
        "exchange": exchange,
        "sec_filing_url": sec_filing_url,
        "ai_report": ai_report,
        "risk_score_short_term": risk_short,
        "risk_score_long_term": risk_long,
    }).execute()