import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os

# --- Configurazione pagina ---
st.set_page_config(page_title="Il Mio Budget Personale", layout="wide")
st.title("💶 Controllo Spese e Proiezione Bancarotta")

# --- Inizializzazione dati (salva in un file CSV) ---
DATA_FILE = "transazioni.csv"

# Se il file non esiste, crea un dataframe con le nuove colonne
if not os.path.exists(DATA_FILE):
    # Crea un dataframe di esempio
    df = pd.DataFrame({
        "Data": [datetime.now().date() - timedelta(days=i) for i in range(10, 0, -1)],
        "Categoria": ["Alimentari"] * 3 + ["Bollette"] * 2 + ["Svago"] * 3 + ["Trasporti"] * 2,
        "Descrizione": ["Spesa", "Panetteria", "Supermercato", "Luce", "Gas", "Cinema", "Cena", "Bar", "Carburante", "Biglietto"],
        "Importo": [-45, -50, -32, -120, -80, -25, -30, -15, -40, -20],
        "Contenitore": ["Contanti"] * 3 + ["Conto Fineco"] * 2 + ["Contanti"] * 3 + ["Conto Revolut"] * 2,
        "TipoSpesa": ["Necessaria"] * 5 + ["Extra"] * 3 + ["Necessaria"] * 2,
    })
    df.to_csv(DATA_FILE, index=False)
else:
    df = pd.read_csv(DATA_FILE)
    df["Data"] = pd.to_datetime(df["Data"]).dt.date
    
    # Migrazione dati per le nuove colonne
    if "Contenitore" not in df.columns:
        df["Contenitore"] = "Contanti"
    if "TipoSpesa" not in df.columns:
        df["TipoSpesa"] = "Necessaria"
        categorie_extra = ["Svago", "Cena", "Bar", "Cinema", "Ristorante", "Vestiti", "Regali"]
        df.loc[df["Categoria"].isin(categorie_extra), "TipoSpesa"] = "Extra"

# --- SIDEBAR: INPUT MOVIMENTO ---
st.sidebar.header("➕ Inserisci Movimento")
with st.sidebar.form("new_transaction"):
    col1, col2 = st.columns(2)
    with col1:
        tipo = st.selectbox("Tipo", ["Uscita (-)", "Entrata (+)"])
    with col2:
        importo = st.number_input("Importo (€)", min_value=0.01, step=0.50)
    
    categoria = st.text_input("Categoria (es. Affitto, Ristorante)")
    descrizione = st.text_input("Descrizione")
    contenitore = st.selectbox("Dove sono questi soldi?", ["Contanti", "Conto Fineco", "Conto Revolut", "Spiccioli"])
    
    if tipo == "Uscita (-)":
        tipo_spesa = st.selectbox("Tipo di spesa", ["Necessaria", "Extra"])
    else:
        tipo_spesa = "Necessaria"
    
    submitted = st.form_submit_button("Aggiungi")
    
    if submitted and importo > 0:
        valore = importo if tipo == "Entrata (+)" else -importo
        nuova_riga = pd.DataFrame({
            "Data": [datetime.now().date()],
            "Categoria": [categoria if categoria else "Varie"],
            "Descrizione": [descrizione if descrizione else "Movimento"],
            "Importo": [valore],
            "Contenitore": [contenitore],
            "TipoSpesa": [tipo_spesa],
        })
        df = pd.concat([df, nuova_riga], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)
        st.rerun()

# --- 🆕 SIDEBAR: NUOVA SEZIONE TRASFERIMENTO ---
st.sidebar.divider()
st.sidebar.header("🔄 Trasferisci tra Conti")
with st.sidebar.form("transfer_form"):
    st.sidebar.caption("Sposta soldi da un contenitore all'altro (es. da Contanti a Conto Fineco)")
    
    col1, col2 = st.columns(2)
    with col1:
        contenitore_da = st.selectbox("Da", ["Contanti", "Conto Fineco", "Conto Revolut", "Spiccioli"], key="transfer_from")
    with col2:
        contenitore_a = st.selectbox("A", ["Contanti", "Conto Fineco", "Conto Revolut", "Spiccioli"], key="transfer_to")
    
    importo_trf = st.number_input("Importo da trasferire (€)", min_value=0.01, step=1.00, key="transfer_amount")
    descrizione_trf = st.text_input("Descrizione (opzionale)", placeholder="es. Prelievo contanti", key="transfer_desc")
    
    transfer_submitted = st.form_submit_button("🔄 Esegui Trasferimento")
    
    if transfer_submitted and importo_trf > 0:
        if contenitore_da == contenitore_a:
            st.error("❌ Non puoi trasferire soldi nello stesso contenitore!")
        else:
            # 1. Uscita dal contenitore "DA"
            riga_uscita = pd.DataFrame({
                "Data": [datetime.now().date()],
                "Categoria": ["Trasferimento"],
                "Descrizione": [descrizione_trf if descrizione_trf else f"Trasferito a {contenitore_a}"],
                "Importo": [-importo_trf],
                "Contenitore": [contenitore_da],
                "TipoSpesa": ["Necessaria"],  # Neutrale per i trasferimenti
            })
            # 2. Entrata nel contenitore "A"
            riga_entrata = pd.DataFrame({
                "Data": [datetime.now().date()],
                "Categoria": ["Trasferimento"],
                "Descrizione": [descrizione_trf if descrizione_trf else f"Ricevuto da {contenitore_da}"],
                "Importo": [importo_trf],
                "Contenitore": [contenitore_a],
                "TipoSpesa": ["Necessaria"],
            })
            
            # Aggiungo entrambe le righe al DataFrame
            df = pd.concat([df, riga_uscita, riga_entrata], ignore_index=True)
            df.to_csv(DATA_FILE, index=False)
            st.rerun()

# --- DASHBOARD PRINCIPALE ---
# Calcoli base
saldo_attuale = df["Importo"].sum()
spese_totali = df[df["Importo"] < 0]["Importo"].sum()
entrate_totali = df[df["Importo"] > 0]["Importo"].sum()

col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 Saldo Totale", f"€ {saldo_attuale:,.2f}")
col2.metric("📈 Entrate totali", f"€ {entrate_totali:,.2f}")
col3.metric("📉 Spese totali", f"€ {abs(spese_totali):,.2f}")
col4.metric("📊 Netto", f"€ {entrate_totali + spese_totali:,.2f}")

# --- SEPARAZIONE PORTAFOGLIO PER CONTENITORE ---
st.divider()
st.subheader("🏦 Separazione del Portafoglio")

saldo_contenitore = df.groupby("Contenitore")["Importo"].sum().reset_index()

if not saldo_contenitore.empty:
    cols = st.columns(len(saldo_contenitore))
    for i, row in saldo_contenitore.iterrows():
        with cols[i % len(cols)]:
            st.metric(f"💵 {row['Contenitore']}", f"€ {row['Importo']:,.2f}")
    
    fig_pie = px.pie(saldo_contenitore, values="Importo", names="Contenitore", 
                     title="Distribuzione del tuo denaro per contenitore",
                     hole=0.4, color_discrete_sequence=px.colors.sequential.Blues_r)
    st.plotly_chart(fig_pie, use_container_width=True)
else:
    st.info("Non hai ancora inserito movimenti per vedere la separazione del portafoglio.")

# --- ANALISI SPESE: NECESSARIE vs EXTRA ---
st.divider()
st.subheader("📊 Analisi Spese: Necessarie vs Extra")

spese_df = df[df["Importo"] < 0]
if not spese_df.empty:
    spese_tipo = spese_df.groupby("TipoSpesa")["Importo"].sum().abs().reset_index()
    
    col1, col2 = st.columns(2)
    with col1:
        necessario = spese_tipo[spese_tipo['TipoSpesa'] == 'Necessaria']['Importo'].sum() if 'Necessaria' in spese_tipo['TipoSpesa'].values else 0
        st.metric("Spese Necessarie", f"€ {necessario:,.2f}")
    with col2:
        extra = spese_tipo[spese_tipo['TipoSpesa'] == 'Extra']['Importo'].sum() if 'Extra' in spese_tipo['TipoSpesa'].values else 0
        st.metric("Spese Extra", f"€ {extra:,.2f}")
    
    fig_bar = px.bar(spese_tipo, x="TipoSpesa", y="Importo", 
                     title="Confronto Spese Necessarie vs Extra",
                     color="TipoSpesa", color_discrete_sequence=["#2E86C1", "#E67E22"],
                     text_auto=True)
    st.plotly_chart(fig_bar, use_container_width=True)
else:
    st.info("Non hai ancora inserito spese per vedere questa analisi.")

# --- CALCOLO RUNWAY (MESI PRIMA DELLA BANCAROTTA) ---
st.divider()
st.subheader("⏳ Proiezione Futura (Runway)")

ultimo_mese = df[df["Data"] >= (datetime.now().date() - timedelta(days=30))]
spesa_giornaliera_media = abs(ultimo_mese[ultimo_mese["Importo"] < 0]["Importo"].mean())
if pd.isna(spesa_giornaliera_media): spesa_giornaliera_media = 0

entrata_giornaliera_media = ultimo_mese[ultimo_mese["Importo"] > 0]["Importo"].mean()
if pd.isna(entrata_giornaliera_media): entrata_giornaliera_media = 0

burn_rate_giornaliero = spesa_giornaliera_media - entrata_giornaliera_media

if burn_rate_giornaliero > 0 and saldo_attuale > 0:
    giorni_rimanenti = saldo_attuale / burn_rate_giornaliero
    mesi_rimanenti = giorni_rimanenti / 30
    st.warning(f"⚠️ Al ritmo attuale, esaurirai i soldi tra **{mesi_rimanenti:.1f} mesi** (circa {int(giorni_rimanenti)} giorni).")
elif saldo_attuale <= 0:
    st.error("🚨 Sei già in bancarotta! Aumenta le entrate o riduci le spese.")
else:
    st.success("✅ Stai risparmiando! Le tue entrate coprono le spese.")

# --- GRAFICO PROIEZIONE A 12 MESI ---
if burn_rate_giornaliero > 0:
    proiezione = []
    saldo_futuro = saldo_attuale
    for i in range(13):
        proiezione.append({"Mese": i, "Saldo Previsto": max(0, saldo_futuro)})
        saldo_futuro -= burn_rate_giornaliero * 30
    
    df_proiezione = pd.DataFrame(proiezione)
    fig = px.line(df_proiezione, x="Mese", y="Saldo Previsto", 
                  title="📉 Andamento del Saldo nei prossimi 12 mesi (se non cambi abitudini)",
                  markers=True)
    fig.add_hline(y=0, line_dash="dash", line_color="red")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Non hai abbastanza dati per calcolare il burn rate, oppure stai risparmiando. Continua ad aggiungere spese!")

# --- TABELLA ULTIME TRANSAZIONI ---
st.divider()
st.subheader("📋 Cronologia Movimenti")
st.dataframe(df.sort_values("Data", ascending=False), use_container_width=True)

# --- BOTTONE PER RESETTARE I DATI ---
if st.button("🗑️ Cancella tutti i dati e ricomincia"):
    os.remove(DATA_FILE)
    st.rerun()
