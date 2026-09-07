import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os

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

# --- Spese Ricorrenti (ora anche Entrate Ricorrenti) ---
if not os.path.exists(RECURRING_FILE):
    # 🆕 Aggiunto campo "TipoMovimento" ("Entrata (+)" o "Uscita (-)")
    df_rec = pd.DataFrame(columns=["Nome", "Importo", "Categoria", "Contenitore", "Tipo", "Giorno", "Attiva", "TipoMovimento"])
    df_rec.to_csv(RECURRING_FILE, index=False)
else:
    df_rec = pd.read_csv(RECURRING_FILE)
    if "Attiva" not in df_rec.columns:
        df_rec["Attiva"] = True
    if "Tipo" not in df_rec.columns:
        df_rec["Tipo"] = "Generico"
    # 🆕 Migrazione per vecchie ricorrenze (se non hanno TipoMovimento, le imposto come Uscita per default)
    if "TipoMovimento" not in df_rec.columns:
        df_rec["TipoMovimento"] = "Uscita (-)"

# --- Funzione per applicare le ricorrenze (aggiornata per gestire + e -) ---
def applica_ricorrenze():
    oggi = datetime.now().date()
    modifiche = False
    for _, row in df_rec.iterrows():
        if not row["Attiva"]:
            continue
        giorno = int(row["Giorno"])
        if giorno == 31:
            import calendar
            ultimo_giorno = calendar.monthrange(oggi.year, oggi.month)[1]
            if oggi.day != ultimo_giorno:
                continue
        else:
            if oggi.day != giorno:
                continue
        
        # Controllo duplicati
        già_inserita = df[
            (df["Data"] == oggi) & 
            (df["Descrizione"] == f"RICORRENTE: {row['Nome']}")
        ]
        if not già_inserita.empty:
            continue
        
        # 🆕 Determino il segno dell'importo in base al tipo movimento
        if row["TipoMovimento"] == "Entrata (+)":
            importo_effettivo = abs(row["Importo"])   # Positivo
        else:  # "Uscita (-)"
            importo_effettivo = -abs(row["Importo"])  # Negativo
        
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
    
    if modifiche:
        df.to_csv(DATA_FILE, index=False)
        return True
    return False

if applica_ricorrenze():
    st.toast("📅 Ricorrenze del giorno aggiunte!", icon="✅")

# --- SIDEBAR: INPUT MOVIMENTO ---
# ✅ VERSIONE CORRETTA
with st.sidebar.expander("➕ Inserisci Movimento", expanded=True):
    with st.form("new_transaction"):   # <-- NON usare st.sidebar.form
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

# --- SIDEBAR: TRASFERIMENTO ---
with st.sidebar.expander("🔄 Trasferisci tra Conti", expanded=True):
    with st.form("transfer_form"):   # <-- SENZA st.sidebar.
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

# --- SIDEBAR: GESTIONE RICORRENZE (aggiornata con TipoMovimento) ---
st.sidebar.divider()
st.sidebar.header("🗓️ Spese/Entrate Ricorrenti")

with st.sidebar.expander("➕ Aggiungi nuova ricorrenza", expanded=False):
    with st.form("new_recurring"):
        nome_rec = st.text_input("Nome (es. Affitto, Stipendio, Netflix)")
        col1_rec, col2_rec = st.columns(2)
        with col1_rec:
            importo_rec = st.number_input("Importo (€)", min_value=0.01, step=0.50)
        with col2_rec:
            # 🆕 Scelta se è entrata o uscita
            tipo_mov_rec = st.selectbox("Tipo movimento", ["Uscita (-)", "Entrata (+)"])
        
        categoria_rec = st.text_input("Categoria")
        contenitore_rec = st.selectbox("Contenitore", ["Contanti", "Conto Fineco", "Conto Revolut", "Spiccioli"])
        tipo_rec = st.text_input("Tipo personalizzato (es. Fissa, Extra, Stipendio)", placeholder="Inserisci un tipo")
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
                "TipoMovimento": [tipo_mov_rec],  # 🆕 Salviamo se è Entrata o Uscita
            })
            df_rec = pd.concat([df_rec, nuova_rec], ignore_index=True)
            df_rec.to_csv(RECURRING_FILE, index=False)
            st.rerun()

if not df_rec.empty:
    st.sidebar.subheader("📋 Le tue ricorrenze")
    for idx, row in df_rec.iterrows():
        col1, col2, col3 = st.sidebar.columns([1, 3, 1])
        with col1:
            stato = st.checkbox("✅", value=row["Attiva"], key=f"rec_{idx}")
        with col2:
            # Mostro il segno (+) o (-) davanti all'importo
            segno = "+" if row["TipoMovimento"] == "Entrata (+)" else "-"
            st.write(f"**{row['Nome']}**")
            st.caption(f"{segno} €{row['Importo']:.2f} - Giorno {int(row['Giorno'])} - {row['Tipo']}")
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
    st.sidebar.info("Nessuna ricorrenza. Aggiungine una sopra!")

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

# --- ANALISI PER TIPO ---
st.divider()
st.subheader("📊 Analisi per Tipo (personalizzato)")

spese_df = df[df["Importo"] < 0]
if not spese_df.empty:
    spese_tipo = spese_df.groupby("Tipo")["Importo"].sum().abs().reset_index()
    fig_spese_tipo = px.bar(spese_tipo, x="Tipo", y="Importo", 
                            title="Spese per Tipo",
                            color="Tipo", text_auto=True)
    st.plotly_chart(fig_spese_tipo, use_container_width=True)
else:
    st.info("Nessuna spesa registrata.")

entrate_df = df[df["Importo"] > 0]
if not entrate_df.empty:
    entrate_tipo = entrate_df.groupby("Tipo")["Importo"].sum().reset_index()
    fig_entrate_tipo = px.pie(entrate_tipo, values="Importo", names="Tipo", 
                              title="Entrate per Tipo",
                              hole=0.3)
    st.plotly_chart(fig_entrate_tipo, use_container_width=True)
else:
    st.info("Nessuna entrata registrata.")

# --- RUNWAY ---
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
    st.error("🚨 Sei già in bancarotta!")
else:
    st.success("✅ Stai risparmiando!")

if burn_rate_giornaliero > 0:
    proiezione = []
    saldo_futuro = saldo_attuale
    for i in range(13):
        proiezione.append({"Mese": i, "Saldo Previsto": max(0, saldo_futuro)})
        saldo_futuro -= burn_rate_giornaliero * 30
    df_proiezione = pd.DataFrame(proiezione)
    fig = px.line(df_proiezione, x="Mese", y="Saldo Previsto", 
                  title="📉 Andamento del Saldo nei prossimi 12 mesi",
                  markers=True)
    fig.add_hline(y=0, line_dash="dash", line_color="red")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Non hai abbastanza dati per il calcolo.")

# --- TABELLA CRONOLOGIA ---
st.divider()
st.subheader("📋 Cronologia Movimenti")
st.dataframe(df.sort_values("Data", ascending=False), use_container_width=True)

# --- RESET ---
if st.button("🗑️ Cancella tutti i dati e ricomincia"):
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)
    if os.path.exists(RECURRING_FILE):
        os.remove(RECURRING_FILE)
    st.rerun()
