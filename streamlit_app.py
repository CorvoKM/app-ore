import streamlit as st
import pandas as pd
import re
import io
import requests
from datetime import datetime

# ======= CONFIGURAZIONE =======
st.set_page_config(page_title="Gestione Ore Dipendenti", page_icon="🧾", layout="wide")

NOTION_TOKEN = st.secrets.get("NOTION_TOKEN", None)
NOTION_DATABASE_ID = st.secrets.get("NOTION_DATABASE_ID", None)

# ======= FUNZIONI =======

def parse_employee_csv(file):
    """Analizza un CSV mensile di ore lavorate e restituisce un DataFrame pulito."""
    text = file.getvalue().decode("latin1")
    lines = text.splitlines()
    records = []
    current_name = None
    header = []

    # Riconosce una riga nome cognome seguita da un giorno (es. Baldo Vittorio;01;)
    pattern_name = re.compile(r'^([A-Za-zÀ-ÿ]+\s+[A-Za-zÀ-ÿ]+);(0[1-9]|[12][0-9]|3[01]);')

    for line in lines:
        if pattern_name.match(line):
            current_name = line.split(";")[0].strip()
            header = line.split(";")[1:]
            header = [h.strip() for h in header if h.strip()]
            continue

        if current_name and ";" in line:
            parts = line.split(";")
            label = parts[0].strip()
            values = parts[1:]
            for i, val in enumerate(values):
                val = val.strip().replace(",", ".")
                if val and val not in ["0", ""]:
                    try:
                        ore = float(val)
                    except ValueError:
                        continue
                    giorno = header[i] if i < len(header) else f"Giorno{i+1}"
                    records.append({
                        "Nome": current_name,
                        "Data": giorno,
                        "Tipo": label,
                        "Ore": ore
                    })

    return pd.DataFrame(records)


def send_to_notion(df):
    """Invia i dati alla tabella Notion specificata nei secrets Streamlit."""
    if not (NOTION_TOKEN and NOTION_DATABASE_ID):
        st.warning("⚠️ Token Notion o Database ID mancanti nei secrets. Operazione saltata.")
        return

    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    for _, row in df.iterrows():
        data = {
            "parent": {"database_id": NOTION_DATABASE_ID},
            "properties": {
                "Nome": {"title": [{"text": {"content": row["Nome"]}}]},
                "Data": {"rich_text": [{"text": {"content": str(row["Data"])}}]},
                "Tipo": {"select": {"name": row["Tipo"]}},
                "Ore": {"number": row["Ore"]}
            }
        }
        requests.post("https://api.notion.com/v1/pages", headers=headers, json=data)


# ======= INTERFACCIA STREAMLIT =======
st.title("🧾 Gestione Ore Dipendenti")
st.markdown("Carica i file CSV mensili dei dipendenti per convertirli in formato leggibile o inviarli su Notion.")

uploaded_files = st.file_uploader("📂 Carica uno o più file CSV", type=["csv"], accept_multiple_files=True)

if uploaded_files:
    all_dfs = []

    for file in uploaded_files:
        st.subheader(f"📘 {file.name}")
        df = parse_employee_csv(file)

        if df.empty:
            st.warning(f"Nessun dato riconosciuto nel file **{file.name}**.")
        else:
            st.dataframe(df.head(10))
            all_dfs.append(df)

    if all_dfs:
        combined_df = pd.concat(all_dfs, ignore_index=True)
        st.success("✅ Conversione completata!")

        # Scaricamento CSV
        st.download_button(
            "📥 Scarica CSV pulito",
            data=combined_df.to_csv(index=False).encode("utf-8"),
            file_name="ore_dipendenti_pulito.csv",
            mime="text/csv"
        )

        # ======= VISUALIZZAZIONI =======
        st.subheader("📊 Analisi Grafica")

        col1, col2 = st.columns(2)

        with col1:
            ore_per_dipendente = combined_df.groupby("Nome")["Ore"].sum().sort_values(ascending=False)
            st.bar_chart(ore_per_dipendente, use_container_width=True)

        with col2:
            ore_per_tipo = combined_df.groupby("Tipo")["Ore"].sum().sort_values(ascending=False)
            st.bar_chart(ore_per_tipo, use_container_width=True)

        # ======= INVIO A NOTION =======
        st.divider()
        st.subheader("📤 Invia a Notion")
        if st.button("Invia ora 🚀"):
            send_to_notion(combined_df)
            st.success("✅ Dati inviati a Notion con successo!")
else:
    st.info("⬆️ Carica almeno un file CSV per iniziare.")