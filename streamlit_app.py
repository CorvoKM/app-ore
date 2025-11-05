import streamlit as st
import pandas as pd
import re

# -------------------------------
# FUNZIONE PER PARSARE I FILE CSV
# -------------------------------
def parse_employee_hours(file_content: str):
    lines = [line.strip() for line in file_content.splitlines() if line.strip()]
    employees = {}
    current_name = None
    current_section = {}

    for line in lines:
        # Identifica il nome del dipendente
        if re.match(r"^[A-ZÀ-Ú][a-zà-ú]+\s[A-ZÀ-Ú][a-zà-ú]+", line):
            if current_name:
                employees[current_name] = current_section
            current_name = line.split(";")[0].strip()
            current_section = {}
        elif ";" in line and current_name:
            parts = line.split(";")
            category = parts[0].strip()
            # Se non ci sono numeri dopo il punto e virgola, salta
            if len(parts) < 2:
                continue
            values = [v.strip().replace(",", ".") for v in parts[1:] if v.strip() != ""]
            # Evita righe vuote o senza numeri
            if not values:
                continue
            try:
                total = float(values[-1])
            except ValueError:
                total = 0.0
            current_section[category] = total

    if current_name:
        employees[current_name] = current_section
    return employees


# -------------------------------
# INTERFACCIA STREAMLIT
# -------------------------------
st.set_page_config(page_title="Analisi Ore Dipendenti", layout="wide")
st.title("📊 Analisi Ore Dipendenti (Automatica)")

uploaded_files = st.file_uploader(
    "Carica uno o più file CSV delle ore mensili",
    type=["csv"],
    accept_multiple_files=True,
)

if uploaded_files:
    all_data = {}

    # Unisci i dati di tutti i file caricati
    for uploaded_file in uploaded_files:
        content = uploaded_file.read().decode("latin1")
        employees = parse_employee_hours(content)

        for name, data in employees.items():
            if name not in all_data:
                all_data[name] = {}
            for k, v in data.items():
                all_data[name][k] = all_data[name].get(k, 0) + v

    # Crea DataFrame riepilogativo
    df = pd.DataFrame(all_data).fillna(0).T

    # Gestisci correttamente le colonne previste
    previste_col = [c for c in df.columns if "previste" in c.lower()]
    if previste_col:
        df["Ore Previste Totali"] = df[previste_col].sum(axis=1)
        df.drop(columns=previste_col, inplace=True)
    else:
        df["Ore Previste Totali"] = 0

    # Calcolo ore effettive (escludendo Ore Previste)
    excluded = ["Ore Previste", "Ore Previste Totali"]
    df["Ore Totali Effettive"] = df[
        [col for col in df.columns if col not in excluded]
    ].sum(axis=1)

    # Rapporto rispetto alle ore previste totali
    df["% Completamento"] = (
        (df["Ore Totali Effettive"] / df["Ore Previste Totali"]) * 100
    ).replace([float("inf"), -float("inf")], 0).fillna(0).round(1)

    # -------------------------------
    # SEZIONE RISULTATI
    # -------------------------------
    st.header("📋 Riepilogo per Dipendente")
    st.dataframe(
        df[
            [
                "Ore Previste Totali",
                "Ore Totali Effettive",
                "% Completamento",
            ]
        ].style.format(
            {"Ore Previste Totali": "{:.1f}", "Ore Totali Effettive": "{:.1f}", "% Completamento": "{:.1f}%"}
        ),
        use_container_width=True,
    )

    # -------------------------------
    # SEZIONE GRAFICI
    # -------------------------------
    st.header("📈 Confronto Ore Previste vs Effettive")
    st.bar_chart(
        df[["Ore Previste Totali", "Ore Totali Effettive"]],
        use_container_width=True,
    )

    st.header("📊 Percentuale di Completamento")
    st.bar_chart(
        df[["% Completamento"]],
        use_container_width=True,
    )

    st.success("✅ Analisi completata con successo!")
else:
    st.info("📂 Carica i file CSV per iniziare l'analisi.")
