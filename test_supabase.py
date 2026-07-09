import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

result = client.table("ipo_analyses").insert({
    "ticker": "TEST",
    "company_name": "Entreprise Test",
    "ai_report": "Ceci est un test."
}).execute()

print("Insertion réussie :", result.data)