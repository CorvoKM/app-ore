import streamlit as st
import pandas as pd
import re
import requests

# ======= CONFIGURAZIONE =======
st.set_page_config(page_title="Gestione Ore Dipendenti", page_icon="🧾", layout="wide")

NOTION_TOKEN = st.secrets.get("NOTION_TOKEN", None)
NOTION_DATABASE_ID = st.secrets.get("NOTION_DATABASE_ID", None)

# ======= FUNZIONI =======

def parse_employee_csv(file):
    """
    Analizza un CSV mensile di ore lavorate e restituisce un DataFrame pulito:
    - estrae righe "Tipo" (Ordinarie, Straordinari, Paternità, ecc.) come record giornalieri
    - cattura il valore TOT di "Ore Previste" come 'Ore Previste Totali' (riferimento)
    - evita di inserire la colonna TOT come giorno per non raddoppiare i conti
    """
    text = file.getvalue().decode("latin1")
    lines = text.splitlines()
    records = []
    current_name = None
    header = []
    ore_previste_totali = {}

    # Riconosce una riga "Nome Cognome;01;02;...;TOT" (obbliga che dopo il nome compaia un giorno 01-31)
    pattern_name = re.compile(r'^([A-Za-zÀ-ÿ]+\s+[A-Za-zÀ-ÿ]+);(0[1-9]|[12][0-9]|3[01]);')

    for line in lines:
        if not line or line.strip().startswith(";;;;;;;;;;;;;;;;"):
            continue

        # Inizio nuovo blocco dipendente + header (giorni + eventualmente "TOT")
        if pattern_name.match(line):
            current_name = line.split(";")[0].strip()
            raw_header = line.split(";")[1:]
            # normalizzo header e rimuovo eventuali celle vuote finali
            header = [h.strip() for h in raw_header if h.strip() != ""]
            # ricerca indice della colonna TOT (se presente) per poterla ignorare nei record giornalieri
            tot_index = None
            for idx, h in enumerate(header[::-1]):
                if h.upper() in ("TOT", "TOTAL", "TOTALE", "TOT."):
                    # convert index from reversed list to normal index
                    tot_index = len(header) - 1 - idx
                    break
            # se TOT è presente, rimuoviamolo dalla lista dei giorni che useremo per i record
            if tot_index is not None:
                header_for_days = header[:tot_index]
            else:
                header_for_days = header[:]
            continue

        # Se siamo all'interno di un blocco dipendente e la riga contiene separatore ;
        if current_name and ";" in line:
            parts = line.split(";")
            label = parts[0].strip()
            raw_values = parts[1:]

            # normalize values: keep original length to align con header indices
            values = [v.strip().replace(",", ".") for v in raw_values]

            # ---- GESTIONE ORE PREVISTE ----
            # Se la riga è "Ore Previste" prendi l'ultimo valore numerico come totale di riferimento
            if label.lower().startswith("ore previste"):
                # cerca l'ultimo valore numerico nella riga (scorri da destra a sinistra)
                last_num = None
                for v in reversed(values):
                    if v and re.match(r'^[\d]+(?:[\.,]\d+)?$', v):
                        last_num = v
                        break
                if last_num is not None:
                    try:
                        ore_previste_totali[current_name] = float(last_num.replace(",", "."))
                    except:
                        ore_previste_totali[current_name] = None
                # non generare record giornalieri per "Ore Previste"
                continue

            # ---- GESTIONE ALTRE RIGHE (ore effettive) ----
            # Iteriamo solo sulle colonne che rappresentano giorni (header_for_days)
            for i in range(len(header_for_days)):
                if i >= len(values):
                    continue
                val = values[i]
                if not val or val in ("0", ""):
                    continue
                # se il valore è numerico lo prendo
                if re.match(r'^[\d]+(?:[\.,]\d+)?$', val):
                    try:
                        ore = float(val.replace(",", "."))
                    except:
                        continue
                    giorno = header_for_days[i]  # es. "01", "02", ...
                    records.append({
                        "Nome": current_name,
                        "Data": giorno,
                        "Tipo": label,
                        "Ore": ore
                    })
                else:
                    # non-numerico: skip
                    continue

    df = pd.DataFrame(records)

    # Aggiunge ore previste totali come colonna di riferimento (mappa per nome)
    if not df.empty:
        df["Ore Previste Totali"] = df["Nome"].map(ore_previste_totali)

    return df


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
                "Ore": {"number": row["Ore"]},
                "Ore Previste Totali": {"number": row.get("Ore Previste Totali")}
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

        st.divider()
        st.subheader("📈 Confronto Ore Effettive vs Previste")

        confronto = (
            combined_df.groupby("Nome")[["Ore", "Ore Previste Totali"]]
            .sum()
            .fillna(0)
        )
        confronto["Differenza"] = confronto["Ore"] - confronto["Ore Previste Totali"]

        st.dataframe(confronto)
        st.bar_chart(confronto[["Ore", "Ore Previste Totali"]])

        # ======= INVIO A NOTION =======
        st.divider()
        st.subheader("📤 Invia a Notion")
        if st.button("Invia ora 🚀"):
            send_to_notion(combined_df)
            st.success("✅ Dati inviati a Notion con successo!")
else:
    st.info("⬆️ Carica almeno un file CSV per iniziare.")
