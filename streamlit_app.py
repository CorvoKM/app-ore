import streamlit as st
import pandas as pd
import requests
import datetime

NOTION_TOKEN = st.secrets["NOTION_TOKEN"]
DATABASE_ID = st.secrets["DATABASE_ID"]

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

st.title("📊 Caricatore Ore Dipendenti su Notion")

uploaded_file = st.file_uploader("Carica il file CSV delle ore lavorate", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file, sep=";", encoding="latin1")
    st.write("Anteprima dati:", df.head())

    # Normalizzazione semplice (esempio)
    # Aspetta colonne: Nome, Data, Tipo, Ore
    if all(col in df.columns for col in ["Nome", "Data", "Tipo", "Ore"]):
        if st.button("Invia su Notion"):
            for _, row in df.iterrows():
                data = {
                    "parent": {"database_id": DATABASE_ID},
                    "properties": {
                        "Nome": {"title": [{"text": {"content": str(row["Nome"])}}]},
                        "Data": {"date": {"start": str(row["Data"])}},
                        "Tipo Ore": {"select": {"name": str(row["Tipo"])}},
                        "Ore": {"number": float(row["Ore"])}
                    }
                }

                res = requests.post("https://api.notion.com/v1/pages", headers=headers, json=data)

                if res.status_code != 200:
                    st.error(f"Errore con {row['Nome']} ({row['Data']}): {res.text}")
                    break
            else:
                st.success("✅ Tutti i record sono stati inviati con successo a Notion!")
    else:
        st.warning("Il CSV deve contenere le colonne: Nome, Data, Tipo, Ore")