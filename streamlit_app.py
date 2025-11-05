import streamlit as st
import pandas as pd
import re
import matplotlib.pyplot as plt

st.set_page_config(page_title="Ore Dipendenti - Analisi", layout="wide")

st.title("📊 Analisi Ore Dipendenti")
st.write("Carica i file CSV mensili (ad esempio Agosto, Settembre, Ottobre) per analizzare le ore dei dipendenti.")


# --- PARSER ROBUSTO ---
def parse_employee_csv(file):
    text = file.getvalue().decode("latin1")
    lines = text.splitlines()
    records = []
    current_name = None
    header = []
    ore_previste_totali = {}

    pattern_name = re.compile(r'^([A-Za-zÀ-ÿ]+\s+[A-Za-zÀ-ÿ]+);(0[1-9]|[12][0-9]|3[01]);')

    for line in lines:
        if not line or line.strip().startswith(";;;;;;;;;;;;;;;;"):
            continue

        if pattern_name.match(line):
            current_name = line.split(";")[0].strip()
            raw_header = line.split(";")[1:]
            header = [h.strip() for h in raw_header if h.strip() != ""]

            # Trova colonna TOT e rimuovila
            tot_index = None
            for idx, h in enumerate(header[::-1]):
                if h.upper() in ("TOT", "TOTAL", "TOTALE", "TOT."):
                    tot_index = len(header) - 1 - idx
                    break
            if tot_index is not None:
                header_for_days = header[:tot_index]
            else:
                header_for_days = header[:]
            continue

        if current_name and ";" in line:
            parts = line.split(";")
            label = parts[0].strip()
            raw_values = parts[1:]
            values = [v.strip().replace(",", ".") for v in raw_values]

            # Ore previste totali
            if label.lower().startswith("ore previste"):
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
                continue

            # Altri tipi di ore (ordinarie, straordinari, ferie, malattia, ecc.)
            for i in range(len(header_for_days)):
                if i >= len(values):
                    continue
                val = values[i]
                if not val or val in ("0", ""):
                    continue
                if re.match(r'^[\d]+(?:[\.,]\d+)?$', val):
                    try:
                        ore = float(val.replace(",", "."))
                    except:
                        continue
                    giorno = header_for_days[i]
                    records.append({
                        "Nome": current_name,
                        "Data": giorno,
                        "Tipo": label,
                        "Ore": ore
                    })

    df = pd.DataFrame(records)
    if not df.empty:
        df["Ore Previste Totali"] = df["Nome"].map(ore_previste_totali)

    # 🔧 FIX: elimina eventuali righe con Data = 'TOT'
    df = df[df["Data"].str.upper() != "TOT"]

    return df


# --- UPLOAD FILES ---
uploaded_files = st.file_uploader("📂 Carica uno o più file CSV", type=["csv"], accept_multiple_files=True)

if uploaded_files:
    all_data = []
    for file in uploaded_files:
        df = parse_employee_csv(file)
        df["Mese"] = re.sub(r"[^A-Za-zÀ-ÿ]", "", file.name.replace(".csv", ""))
        all_data.append(df)

    if all_data:
        data = pd.concat(all_data, ignore_index=True)

        # Aggrega ore per dipendente
        ore_totali = data.groupby("Nome")["Ore"].sum().reset_index(name="Ore Totali")
        ore_previste = data[["Nome", "Ore Previste Totali"]].drop_duplicates(subset="Nome")
        merged = pd.merge(ore_totali, ore_previste, on="Nome", how="left")

        # Calcola differenza
        merged["Δ Ore (Effettive - Previste)"] = merged["Ore Totali"] - merged["Ore Previste Totali"]

        st.subheader("📈 Confronto Ore Effettive vs Previste")

        # Grafico a barre ore totali
        fig, ax = plt.subplots(figsize=(10, 5))
        merged.plot(kind="barh", x="Nome", y=["Ore Totali", "Ore Previste Totali"], ax=ax)
        plt.title("Ore Totali vs Previste per Dipendente")
        plt.xlabel("Ore")
        plt.ylabel("Dipendente")
        st.pyplot(fig)

        # Grafico delle differenze
        fig2, ax2 = plt.subplots(figsize=(10, 4))
        merged.plot(kind="barh", x="Nome", y="Δ Ore (Effettive - Previste)", color="gray", ax=ax2)
        plt.title("Differenza tra Ore Effettive e Previste")
        plt.xlabel("Δ Ore")
        plt.ylabel("Dipendente")
        st.pyplot(fig2)

        # Tabella riepilogativa
        st.subheader("📋 Riepilogo")
        st.dataframe(merged.sort_values(by="Δ Ore (Effettive - Previste)", ascending=False), hide_index=True)
