import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os
import calendar

# --- Configurazione pagina ---
st.set_page_config(page_title="Il Mio Budget Personale", layout="wide")
st.title("💶 Controllo Spese e Proiezione Bancarotta")

# --- Inizializzazione dati ---
DATA_FILE = "transazioni.csv"
RECURRING_FILE = "ricorrenze.csv"

# --- Transazioni ---
if not os.path.exists(DATA_FILE):
    df = pd.DataFrame(columns=["Data", "Categoria", "Descrizione", "Importo", "Contenitore", "Tipo"])
    df.to_csv(DATA_FILE, index=False)
else:
    df = pd.read_csv(DATA_FILE)
    df["Data"] = pd.to_datetime(df["Data"]).dt.date
    if "Tipo" not in df.columns:
        if "TipoSpesa" in df.columns:
            df.rename(columns={"TipoSpesa": "Tipo"}, inplace=True)
        else:
            df["Tipo"] = "Generico"
    if "Contenitore" not in df.columns:
        df["Contenitore"] = "Contanti"

# --- Ricorrenze (incluse le Rate) ---
if not os.path.exists(RECURRING_FILE):
    df_rec = pd.DataFrame(columns=[
        "Nome", "Importo", "Categoria", "Contenitore", "Tipo",
        "Giorno", "Attiva", "TipoMovimento", "TipoRicorrenza",
        "DataInizio", "RateTotali", "RatePagate"
    ])
    df_rec.to_csv(RECURRING_FILE, index=False)
else:
    df_rec = pd.read_csv(RECURRING_FILE)
    if "Attiva" not in df_rec.columns:
        df_rec["Attiva"] = True
    if "Tipo" not in df_rec.columns:
        df_rec["Tipo"] = "Generico"
    if "TipoMovimento" not in df_rec.columns:
        df_rec["TipoMovimento"] = "Uscita (-)"
    if "TipoRicorrenza" not in df_rec.columns:
        df_rec["TipoRicorrenza"] = "Normale"
    if "DataInizio" not in df_rec.columns:
        df_rec["DataInizio"] = pd.NA
    if "RateTotali" not in df_rec.columns:
        df_rec["RateTotali"] = 1
    if "RatePagate" not in df_rec.columns:
        df_rec["RatePagate"] = 0

# --- Funzione per applicare le ricorrenze (supporta anche le Rate) ---
def applica_ricorrenze():
    oggi = datetime.now().date()
    modifiche = False
    
    for idx, row in df_rec.iterrows():
        if not row["Attiva"]:
            continue
        
        # --- RICORRENZA NORMALE ---
        if row["TipoRicorrenza"] == "Normale":
            giorno = int(row["Giorno"])
            if giorno == 31:
                ultimo_giorno = calendar.monthrange(oggi.year, oggi.month)[1]
                if oggi.day != ultimo_giorno:
                    continue
            else:
                if oggi.day != giorno:
                    continue
            
            già_inserita = df[
                (df["Data"] == oggi) & 
                (df["Descrizione"] == f"RICORRENTE: {row['Nome']}")
            ]
            if not già_inserita.empty:
                continue
            
            if row["TipoMovimento"] == "Entrata (+)":
                importo_effettivo = abs(row["Importo"])
            else:
                importo_effettivo = -abs(row["Importo"])
            
            nuova_riga = pd.DataFrame({
                "Data": [oggi],
                "Categoria": [row["Categoria"]],
                "Descrizione": [f"RICORRENTE: {row['Nome']}"],
                "Importo": [importo_effettivo],
                "Contenitore": [row["Contenitore"]],
                "Tipo": [row["Tipo"]],
            })
            df.loc[len(df)] = nuova_riga.iloc[0]
            modifiche = True
        
        # --- RICORRENZA A RATE ---
        elif row["TipoRicorrenza"] == "Rate":
            if row["RatePagate"] >= row["RateTotali"]:
                continue
            
            data_inizio = pd.to_datetime(row["DataInizio"]).date()
            mesi_da_aggiungere = int(row["RatePagate"])
            anno = data_inizio.year
            mese = data_inizio.month + mesi_da_aggiungere
            while mese > 12:
                mese -= 12
                anno += 1
            giorno_rata = data_inizio.day
            if giorno_rata == 31:
                ultimo_giorno = calendar.monthrange(anno, mese)[1]
                giorno_rata = ultimo_giorno
            
            data_rata = datetime(anno, mese, giorno_rata).date()
            
            if oggi == data_rata:
                già_inserita = df[
                    (df["Data"] == oggi) & 
                    (df["Descrizione"] == f"RATA: {row['Nome']} ({int(row['RatePagate'])+1}/{int(row['RateTotali'])})")
                ]
                if not già_inserita.empty:
                    continue
                
                importo_rata = abs(row["Importo"]) / row["RateTotali"]
                if row["TipoMovimento"] == "Entrata (+)":
                    importo_effettivo = importo_rata
                else:
                    importo_effettivo = -importo_rata
                
                nuova_riga = pd.DataFrame({
                    "Data": [oggi],
                    "Categoria": [row["Categoria"]],
                    "Descrizione": [f"RATA: {row['Nome']} ({int(row['RatePagate'])+1}/{int(row['RateTotali'])})"],
                    "Importo": [importo_effettivo],
                    "Contenitore": [row["Contenitore"]],
                    "Tipo": [row["Tipo"]],
                })
                df.loc[len(df)] = nuova_riga.iloc[0]
                df_rec.at[idx, "RatePagate"] = row["RatePagate"] + 1
                modifiche = True
    
    if modifiche:
        df.to_csv(DATA_FILE, index=False)
        df_rec.to_csv(RECURRING_FILE, index=False)
        return True
    return False

if applica_ricorrenze():
    st.toast("📅 Ricorrenze del giorno aggiunte!", icon="✅")

# --- SIDEBAR ---

st.sidebar.markdown("# 💰 Menù Principale")

# --- 1. Inserisci Movimento ---
with st.sidebar.expander("➕ Inserisci Movimento", expanded=True):
    with st.form("new_transaction"):
        col1, col2 = st.columns(2)
        with col1:
            tipo_mov = st.selectbox("Tipo", ["Uscita (-)", "Entrata (+)"])
        with col2:
            importo = st.number_input("Importo (€)", min_value=0.01, step=0.50)
        
        categoria = st.text_input("Categoria (es. Affitto, Ristorante)")
        descrizione = st.text_input("Descrizione")
        contenitore = st.selectbox("Contenitore", ["Contanti", "Conto Fineco", "Conto Revolut", "Spiccioli"])
        tipo_personalizzato = st.text_input("Tipo (es. Necessaria, Extra, Fissa, Stipendio, ...)", placeholder="Inserisci un tipo a piacere")
        
        submitted = st.form_submit_button("Aggiungi")
        
        if submitted and importo > 0:
            valore = importo if tipo_mov == "Entrata (+)" else -importo
            if not tipo_personalizzato.strip():
                tipo_personalizzato = "Generico"
            nuova_riga = pd.DataFrame({
                "Data": [datetime.now().date()],
                "Categoria": [categoria if categoria else "Varie"],
                "Descrizione": [descrizione if descrizione else "Movimento"],
                "Importo": [valore],
                "Contenitore": [contenitore],
                "Tipo": [tipo_personalizzato],
            })
            df = pd.concat([df, nuova_riga], ignore_index=True)
            df.to_csv(DATA_FILE, index=False)
            st.rerun()

# --- 2. Trasferimento tra Conti ---
with st.sidebar.expander("🔄 Trasferisci tra Conti", expanded=True):
    with st.form("transfer_form"):
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
                riga_uscita = pd.DataFrame({
                    "Data": [datetime.now().date()],
                    "Categoria": ["Trasferimento"],
                    "Descrizione": [descrizione_trf if descrizione_trf else f"Trasferito a {contenitore_a}"],
                    "Importo": [-importo_trf],
                    "Contenitore": [contenitore_da],
                    "Tipo": ["Trasferimento"],
                })
                riga_entrata = pd.DataFrame({
                    "Data": [datetime.now().date()],
                    "Categoria": ["Trasferimento"],
                    "Descrizione": [descrizione_trf if descrizione_trf else f"Ricevuto da {contenitore_da}"],
                    "Importo": [importo_trf],
                    "Contenitore": [contenitore_a],
                    "Tipo": ["Trasferimento"],
                })
                df = pd.concat([df, riga_uscita, riga_entrata], ignore_index=True)
                df.to_csv(DATA_FILE, index=False)
                st.rerun()

# --- 3. Spese/Entrate Ricorrenti + Rate ---
with st.sidebar.expander("🗓️ Spese/Entrate Ricorrenti", expanded=False):
    
    # Sottomenu: Aggiungi Ricorrenza Normale
    with st.expander("➕ Aggiungi ricorrenza normale", expanded=False):
        with st.form("new_recurring"):
            nome_rec = st.text_input("Nome (es. Affitto, Stipendio, Netflix)")
            col1_rec, col2_rec = st.columns(2)
            with col1_rec:
                importo_rec = st.number_input("Importo (€)", min_value=0.01, step=0.50)
            with col2_rec:
                tipo_mov_rec = st.selectbox("Tipo movimento", ["Uscita (-)", "Entrata (+)"])
            
            categoria_rec = st.text_input("Categoria")
            contenitore_rec = st.selectbox("Contenitore", ["Contanti", "Conto Fineco", "Conto Revolut", "Spiccioli"])
            tipo_rec = st.text_input("Tipo personalizzato", placeholder="es. Fissa, Extra, Stipendio")
            giorno_rec = st.number_input("Giorno del mese (1-31)", min_value=1, max_value=31, value=1, step=1)
            st.caption("💡 Usa 31 per l'ultimo giorno del mese")
            
            aggiungi_rec = st.form_submit_button("➕ Aggiungi Ricorrenza")
            
            if aggiungi_rec:
                if not tipo_rec.strip():
                    tipo_rec = "Generico"
                nuova_rec = pd.DataFrame({
                    "Nome": [nome_rec if nome_rec else f"Ricorrenza {len(df_rec)+1}"],
                    "Importo": [importo_rec],
                    "Categoria": [categoria_rec if categoria_rec else "Varie"],
                    "Contenitore": [contenitore_rec],
                    "Tipo": [tipo_rec],
                    "Giorno": [giorno_rec],
                    "Attiva": [True],
                    "TipoMovimento": [tipo_mov_rec],
                    "TipoRicorrenza": ["Normale"],
                    "DataInizio": [pd.NA],
                    "RateTotali": [1],
                    "RatePagate": [0],
                })
                df_rec = pd.concat([df_rec, nuova_rec], ignore_index=True)
                df_rec.to_csv(RECURRING_FILE, index=False)
                st.rerun()
    
    # Sottomenu: Aggiungi Rate
    with st.expander("📅 Aggiungi pagamento a rate", expanded=False):
        with st.form("new_rate"):
            nome_rate = st.text_input("Nome (es. PayPal 3 rate, TV rate)")
            col1_rate, col2_rate = st.columns(2)
            with col1_rate:
                importo_totale_rate = st.number_input("Importo totale (€)", min_value=0.01, step=0.50)
            with col2_rate:
                num_rate = st.number_input("Numero rate totali", min_value=1, max_value=36, value=3, step=1)
            
            data_inizio_rate = st.date_input("Data della prima rata", value=datetime.now().date())
            categoria_rate = st.text_input("Categoria")
            contenitore_rate = st.selectbox("Contenitore", ["Contanti", "Conto Fineco", "Conto Revolut", "Spiccioli"], key="rate_contenitore")
            tipo_rate = st.text_input("Tipo personalizzato", placeholder="es. Fissa, Extra")
            tipo_mov_rate = st.selectbox("Tipo movimento", ["Uscita (-)", "Entrata (+)"], key="rate_tipo_mov")
            
            st.caption("💡 Le rate verranno aggiunte automaticamente ogni mese alla stessa data della prima rata.")
            
            aggiungi_rate = st.form_submit_button("➕ Aggiungi Rate")
            
            if aggiungi_rate:
                if not tipo_rate.strip():
                    tipo_rate = "Generico"
                nuova_rec = pd.DataFrame({
                    "Nome": [nome_rate if nome_rate else f"Rate {len(df_rec)+1}"],
                    "Importo": [importo_totale_rate],
                    "Categoria": [categoria_rate if categoria_rate else "Varie"],
                    "Contenitore": [contenitore_rate],
                    "Tipo": [tipo_rate],
                    "Giorno": [data_inizio_rate.day],
                    "Attiva": [True],
                    "TipoMovimento": [tipo_mov_rate],
                    "TipoRicorrenza": ["Rate"],
                    "DataInizio": [data_inizio_rate],
                    "RateTotali": [num_rate],
                    "RatePagate": [0],
                })
                df_rec = pd.concat([df_rec, nuova_rec], ignore_index=True)
                df_rec.to_csv(RECURRING_FILE, index=False)
                st.rerun()
    
    # --- Mostra le ricorrenze esistenti ---
    if not df_rec.empty:
        st.sidebar.subheader("📋 Le tue ricorrenze")
        for idx, row in df_rec.iterrows():
            col1, col2, col3 = st.sidebar.columns([1, 3, 1])
            with col1:
                stato = st.checkbox("✅", value=row["Attiva"], key=f"rec_{idx}")
            with col2:
                if row["TipoRicorrenza"] == "Normale":
                    segno = "+" if row["TipoMovimento"] == "Entrata (+)" else "-"
                    st.write(f"**{row['Nome']}**")
                    st.caption(f"{segno} €{row['Importo']:.2f} - Giorno {int(row['Giorno'])} - {row['Tipo']}")
                else:
                    segno = "+" if row["TipoMovimento"] == "Entrata (+)" else "-"
                    st.write(f"**{row['Nome']}** (Rate)")
                    st.caption(f"{segno} €{row['Importo']/row['RateTotali']:.2f} rata - {int(row['RatePagate'])}/{int(row['RateTotali'])} pagate - {row['Tipo']}")
            with col3:
                if st.button("🗑️", key=f"del_{idx}"):
                    df_rec = df_rec.drop(idx).reset_index(drop=True)
                    df_rec.to_csv(RECURRING_FILE, index=False)
                    st.rerun()
            if stato != row["Attiva"]:
                df_rec.at[idx, "Attiva"] = stato
                df_rec.to_csv(RECURRING_FILE, index=False)
                st.rerun()
    else:
        st.sidebar.info("Nessuna ricorrenza.")

# --- DASHBOARD PRINCIPALE ---
saldo_attuale = df["Importo"].sum()
spese_totali = df[df["Importo"] < 0]["Importo"].sum()
entrate_totali = df[df["Importo"] > 0]["Importo"].sum()

col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 Saldo Totale", f"€ {saldo_attuale:,.2f}")
col2.metric("📈 Entrate totali", f"€ {entrate_totali:,.2f}")
col3.metric("📉 Spese totali", f"€ {abs(spese_totali):,.2f}")
col4.metric("📊 Netto", f"€ {entrate_totali + spese_totali:,.2f}")

# --- SEPARAZIONE PORTAFOGLIO ---
st.divider()
st.subheader("🏦 Separazione del Portafoglio")

saldo_contenitore = df.groupby("Contenitore")["Importo"].sum().reset_index()
if not saldo_contenitore.empty:
    cols = st.columns(len(saldo_contenitore))
    for i, row in saldo_contenitore.iterrows():
        with cols[i % len(cols)]:
            st.metric(f"💵 {row['Contenitore']}", f"€ {row['Importo']:,.2f}")
    fig_pie = px.pie(saldo_contenitore, values="Importo", names="Contenitore", 
                     title="Distribuzione del denaro per contenitore",
                     hole=0.4, color_discrete_sequence=px.colors.sequential.Blues_r)
    st.plotly_chart(fig_pie, use_container_width=True)
else:
    st.info("Non hai ancora movimenti.")

# --- ANALISI PER TIPO (storiche) ---
st.divider()
st.subheader("📊 Analisi per Tipo (spese già sostenute)")

# Spese storiche - grafico a torta e barre
spese_df = df[df["Importo"] < 0]
if not spese_df.empty:
    spese_tipo = spese_df.groupby("Tipo")["Importo"].sum().abs().reset_index()
    
    col1, col2 = st.columns(2)
    with col1:
        fig_spese_pie = px.pie(spese_tipo, values="Importo", names="Tipo",
                               title="Spese Storiche per Tipo (%)",
                               hole=0.3, color_discrete_sequence=px.colors.sequential.Reds_r)
        st.plotly_chart(fig_spese_pie, use_container_width=True)
    with col2:
        fig_spese_bar = px.bar(spese_tipo, x="Tipo", y="Importo",
                               title="Spese Storiche (€)",
                               color="Tipo", text_auto=True)
        st.plotly_chart(fig_spese_bar, use_container_width=True)
else:
    st.info("Nessuna spesa registrata.")

# --- SPESE RICORRENTI FUTURE (prossimi 12 mesi) ---
st.divider()
st.subheader("📊 Spese Ricorrenti Future (programmate, nei prossimi 12 mesi)")

def calcola_spese_ricorrenti_future(mesi=12):
    oggi = datetime.now().date()
    spese_future_per_tipo = {}
    
    for _, row in df_rec.iterrows():
        if not row["Attiva"]:
            continue
        # Solo spese (negative) - escludiamo entrate e trasferimenti
        if row["TipoMovimento"] == "Entrata (+)" or row["Importo"] <= 0:
            continue
        
        if row["TipoRicorrenza"] == "Normale":
            giorno = int(row["Giorno"])
            # Conta quante volte la spesa si verifica nei prossimi 12 mesi
            # partendo dal mese corrente
            for mese_offset in range(mesi + 1):  # include il mese corrente
                # Calcola l'anno e mese target
                anno = oggi.year
                mese = oggi.month + mese_offset
                while mese > 12:
                    mese -= 12
                    anno += 1
                
                # Determina il giorno effettivo del mese
                ultimo_giorno = calendar.monthrange(anno, mese)[1]
                if giorno == 31 or giorno > ultimo_giorno:
                    giorno_effettivo = ultimo_giorno
                else:
                    giorno_effettivo = giorno
                
                # Costruisci la data target
                data_target = datetime(anno, mese, giorno_effettivo).date()
                
                # Se la data è già passata, salta (ma solo se è il mese corrente)
                if mese_offset == 0 and data_target < oggi:
                    continue
                
                # Conta questa spesa
                importo_totale = abs(row["Importo"])
                tipo = row["Tipo"] if row["Tipo"] else "Generico"
                spese_future_per_tipo[tipo] = spese_future_per_tipo.get(tipo, 0) + importo_totale
        
        elif row["TipoRicorrenza"] == "Rate":
            rate_pagate = row["RatePagate"]
            rate_totali = row["RateTotali"]
            rate_rimanenti = max(0, rate_totali - rate_pagate)
            # Considera solo le rate nei prossimi 12 mesi
            rate_nei_prossimi_mesi = min(rate_rimanenti, mesi + 1)  # +1 per includere il mese corrente
            if rate_nei_prossimi_mesi == 0:
                continue
            importo_rata = abs(row["Importo"]) / rate_totali
            importo_totale = importo_rata * rate_nei_prossimi_mesi
            tipo = row["Tipo"] if row["Tipo"] else "Generico"
            spese_future_per_tipo[tipo] = spese_future_per_tipo.get(tipo, 0) + importo_totale
    
    if spese_future_per_tipo:
        return pd.DataFrame(list(spese_future_per_tipo.items()), columns=["Tipo", "Importo"])
    else:
        return None

df_future = calcola_spese_ricorrenti_future(12)

if df_future is not None and not df_future.empty:
    col1, col2 = st.columns(2)
    with col1:
        fig_future_pie = px.pie(df_future, values="Importo", names="Tipo",
                                title="Spese Future per Tipo (%)",
                                hole=0.3, color_discrete_sequence=px.colors.sequential.Oranges_r)
        st.plotly_chart(fig_future_pie, use_container_width=True)
    with col2:
        fig_future_bar = px.bar(df_future, x="Tipo", y="Importo",
                                title="Spese Future (€)",
                                color="Tipo", text_auto=True)
        st.plotly_chart(fig_future_bar, use_container_width=True)
else:
    st.info("Nessuna spesa ricorrente futura programmata.")

# --- ENTRATE (storiche) a torta ---
st.divider()
st.subheader("📊 Entrate (storiche)")
entrate_df = df[df["Importo"] > 0]
if not entrate_df.empty:
    entrate_tipo = entrate_df.groupby("Tipo")["Importo"].sum().reset_index()
    fig_entrate_pie = px.pie(entrate_tipo, values="Importo", names="Tipo",
                             title="Entrate per Tipo (%)",
                             hole=0.3)
    st.plotly_chart(fig_entrate_pie, use_container_width=True)
else:
    st.info("Nessuna entrata registrata.")
# --- PROIEZIONE FUTURA (basata su ricorrenze programmate) ---
st.divider()
st.subheader("⏳ Proiezione Futura (Runway)")

# Calcolo del burn rate storico (per i messaggi di avviso)
ultimo_mese = df[df["Data"] >= (datetime.now().date() - timedelta(days=30))]
spesa_giornaliera_media = abs(ultimo_mese[ultimo_mese["Importo"] < 0]["Importo"].mean())
if pd.isna(spesa_giornaliera_media): spesa_giornaliera_media = 0
entrata_giornaliera_media = ultimo_mese[ultimo_mese["Importo"] > 0]["Importo"].mean()
if pd.isna(entrata_giornaliera_media): entrata_giornaliera_media = 0
burn_rate_storico = spesa_giornaliera_media - entrata_giornaliera_media

if burn_rate_storico > 0 and saldo_attuale > 0:
    giorni_rimanenti = saldo_attuale / burn_rate_storico
    mesi_rimanenti = giorni_rimanenti / 30
    st.warning(f"⚠️ Al ritmo storico, esaurirai i soldi tra **{mesi_rimanenti:.1f} mesi** (circa {int(giorni_rimanenti)} giorni).")
elif saldo_attuale <= 0:
    st.error("🚨 Sei già in bancarotta!")
else:
    st.success("✅ Stai risparmiando!")

# --- NUOVA PROIEZIONE BASATA SU RICORRENZE PROGRAMMATE ---
def calcola_proiezione_ricorrenze(mesi=12):
    """
    Calcola il saldo futuro mese per mese considerando le ricorrenze attive.
    Restituisce una lista di dizionari con Mese e Saldo Previsto.
    """
    oggi = datetime.now().date()
    saldo = saldo_attuale
    proiezione = [{"Mese": 0, "Saldo Previsto": saldo}]
    
    for mese_offset in range(1, mesi + 1):
        # Calcola la data del mese corrente (approssimativa, 1° giorno del mese)
        anno = oggi.year
        mese = oggi.month + mese_offset
        while mese > 12:
            mese -= 12
            anno += 1
        
        # Per ogni ricorrenza attiva, calcola l'importo che si applicherebbe in questo mese
        totale_mese = 0
        for _, row in df_rec.iterrows():
            if not row["Attiva"]:
                continue
            
            # RICORRENZA NORMALE
            if row["TipoRicorrenza"] == "Normale":
                giorno = int(row["Giorno"])
                # Se il giorno è 31, usiamo l'ultimo giorno del mese
                if giorno == 31:
                    ultimo_giorno = calendar.monthrange(anno, mese)[1]
                    giorno = ultimo_giorno
                # Controlliamo se il giorno esiste nel mese (es. 31 febbraio non esiste)
                if giorno > calendar.monthrange(anno, mese)[1]:
                    giorno = calendar.monthrange(anno, mese)[1]
                
                # Se oggi è già passato il giorno di questo mese, la ricorrenza è già stata applicata
                # (per la proiezione, consideriamo che verrà applicata)
                if row["TipoMovimento"] == "Entrada (+)":
                    totale_mese += abs(row["Importo"])
                else:
                    totale_mese -= abs(row["Importo"])
            
            # RICORRENZA A RATE
            elif row["TipoRicorrenza"] == "Rate":
                if row["RatePagate"] >= row["RateTotali"]:
                    continue
                
                data_inizio = pd.to_datetime(row["DataInizio"]).date()
                # Controlliamo se la rata cade in questo mese
                # Calcoliamo il numero di rate che dovrebbero essere pagate entro questo mese
                mesi_trascorsi = (anno - data_inizio.year) * 12 + (mese - data_inizio.month)
                rate_dovute = min(mesi_trascorsi + 1, row["RateTotali"])
                rate_già_pagate = row["RatePagate"]
                
                if rate_dovute > rate_già_pagate:
                    importo_rata = abs(row["Importo"]) / row["RateTotali"]
                    if row["TipoMovimento"] == "Entrata (+)":
                        totale_mese += importo_rata
                    else:
                        totale_mese -= importo_rata
        
        saldo += totale_mese
        proiezione.append({"Mese": mese_offset, "Saldo Previsto": max(0, saldo)})
    
    return proiezione

# Genera la proiezione su 12 mesi
proiezione = calcola_proiezione_ricorrenze(12)
df_proiezione = pd.DataFrame(proiezione)

# Mostra il grafico
fig = px.line(df_proiezione, x="Mese", y="Saldo Previsto", 
              title="📉 Andamento del Saldo nei prossimi 12 mesi (considerando le ricorrenze programmate)",
              markers=True)
fig.add_hline(y=0, line_dash="dash", line_color="red")
st.plotly_chart(fig, use_container_width=True)

# Mostra anche i dati storici se esistono
if not df.empty:
    st.caption("💡 La proiezione tiene conto delle tue spese/entrate ricorrenti attive (normali e rate).")

# --- TABELLE ENTRATE E USCITE SEPARATE CON COLORI E DUE DECIMALI ---
st.divider()
st.subheader("📋 Entrate")
entrate_df = df[df["Importo"] > 0].sort_values("Data", ascending=False)
if not entrate_df.empty:
    st.dataframe(
        entrate_df.style
        .map(lambda v: 'color: green' if v > 0 else '', subset=['Importo'])
        .format("€ {:.2f}", subset=['Importo']),
        use_container_width=True
    )
else:
    st.info("Nessuna entrata registrata.")

st.subheader("📋 Uscite")
uscite_df = df[df["Importo"] < 0].sort_values("Data", ascending=False)
if not uscite_df.empty:
    st.dataframe(
        uscite_df.style
        .map(lambda v: 'color: red' if v < 0 else '', subset=['Importo'])
        .format("€ {:.2f}", subset=['Importo']),
        use_container_width=True
    )
else:
    st.info("Nessuna uscita registrata.")

# --- RESET ---
if st.button("🗑️ Cancella tutti i dati e ricomincia"):
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)
    if os.path.exists(RECURRING_FILE):
        os.remove(RECURRING_FILE)
    st.rerun()
