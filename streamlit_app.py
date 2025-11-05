import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Analisi Ore Dipendenti", layout="wide")
st.title("📊 Analisi Ore Dipendenti")

# -------------------------------
# FUNZIONE PER LEGGERE I CSV
# -------------------------------
def parse_employee_hours(file_content: str):
    lines = [line.strip() for line in file_content.splitlines() if line.strip()]
    employees = {}
    current_name = None
    current_data = {}

    for line in lines:
        # Cerca una riga che sembra un nome e cognome
        if re.match(r"^[A-ZÀ-Ú][a-zà-ú]+ [A-ZÀ-Ú][a-zà-ú]+", line):
            # Salva il precedente dipendente
            if current_name:
                employees[current_name] = current_data
            current_name = line.split(";")[0].strip()
            current_data = {}
        elif ";" in line and current_name:
            parts = line.split(";")
            key = parts[0].strip()
            # Salta se la riga non contiene numeri
            if len(parts) < 2:
                continue
            numbers = [x.strip().replace(",", ".") for x in parts[1:] if x.strip()]
            if not numbers:
                continue
            try:
                value = float(numbers[-1])
            except ValueError:
                continue
            current_data[key] = value

    if current_name:
        employees[current_name] = current_data
    return employees

# -------------------------------
# INTERFACCIA STREAMLIT
# -------------------------------
uploaded_files = st.file_uploader(
    "Carica i file CSV delle ore mensili (es. Settembre, Ottobre...)",
    type=["csv"],
    accept_multiple_files=True,
)

if uploaded_files:
    all_data = {}

    for uploaded_file in uploaded_files:
        content = uploaded_file.read().decode("latin1")
        parsed = parse_employee_hours(content)

        for name, data in parsed.items():
            if name not in all_data:
                all_data[name] = {}
            for key, value in data.items():
                all_data[name][key] = all_data[name].get(key, 0) + value

    # Costruisci DataFrame
    df = pd.DataFrame(all_data).fillna(0).T

    # Identifica colonne previste
    previste_cols = [c for c in df.columns if "previste" in c.lower()]
    df["Ore Previste Totali"] = df[previste_cols].sum(axis=1) if previste_cols else 0

    # Escludi le colonne previste dal calcolo effettivo
    effettive_cols = [c for c in df.columns if c not in previste_cols + ["Ore Previste Totali"]]
    df["Ore Totali Effettive"] = df[effettive_cols].sum(axis=1)

    # Calcola percentuale
    df["% Completamento"] = (
        (df["Ore Totali Effettive"] / df["Ore Previste Totali"]) * 100
    ).replace([float("inf"), -float("inf")], 0).fillna(0).round(1)

    # -------------------------------
    # RIEPILOGO
    # -------------------------------
    st.header("📋 Riepilogo per Dipendente")
    st.dataframe(
        df[["Ore Previste Totali", "Ore Totali Effettive", "% Completamento"]]
        .sort_values("Ore Totali Effettive", ascending=False)
        .style.format({
            "Ore Previste Totali": "{:.1f}",
            "Ore Totali Effettive": "{:.1f}",
            "% Completamento": "{:.1f}%"
        }),
        use_container_width=True
    )

    # -------------------------------
    # GRAFICI STREAMLIT
    # -------------------------------
    st.header("📈 Confronto Ore Previste vs Effettive")
    st.bar_chart(df[["Ore Previste Totali", "Ore Totali Effettive"]])

    st.header("📊 Percentuale di Completamento")
    st.bar_chart(df[["% Completamento"]])

    st.success("✅ Analisi completata con successo!")
else:
    st.info("📂 Carica i file CSV per iniziare l'analisi.")
