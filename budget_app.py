# =============================================================================
# SIDEBAR COMPLETAMENTE ORGANIZZATA CON MENU A TENDINA
# =============================================================================

st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=80)  # Opzionale: icona in alto
st.sidebar.title("💰 Menù Principale")

# -----------------------------------------------------------------------------
# 1. MENU A TENDINA: INSERISCI MOVIMENTO
# -----------------------------------------------------------------------------
with st.sidebar.expander("➕ Inserisci Movimento", expanded=True):  # expanded=True lo apre di default
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

# -----------------------------------------------------------------------------
# 2. MENU A TENDINA: TRASFERIMENTO TRA CONTI
# -----------------------------------------------------------------------------
with st.sidebar.expander("🔄 Trasferisci tra Conti", expanded=False):
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

# -----------------------------------------------------------------------------
# 3. MENU A TENDINA: SPESE/ENTRATE RICORRENTI
# -----------------------------------------------------------------------------
with st.sidebar.expander("🗓️ Spese/Entrate Ricorrenti", expanded=False):
    with st.expander("➕ Aggiungi nuova ricorrenza", expanded=False):
        with st.form("new_recurring"):
            nome_rec = st.text_input("Nome (es. Affitto, Stipendio, Netflix)")
            col1_rec, col2_rec = st.columns(2)
            with col1_rec:
                importo_rec = st.number_input("Importo (€)", min_value=0.01, step=0.50)
            with col2_rec:
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
                    "TipoMovimento": [tipo_mov_rec],
                })
                df_rec = pd.concat([df_rec, nuova_rec], ignore_index=True)
                df_rec.to_csv(RECURRING_FILE, index=False)
                st.rerun()
    
    if not df_rec.empty:
        st.subheader("📋 Le tue ricorrenze")
        for idx, row in df_rec.iterrows():
            col1, col2, col3 = st.columns([1, 3, 1])
            with col1:
                stato = st.checkbox("✅", value=row["Attiva"], key=f"rec_{idx}")
            with col2:
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
        st.info("Nessuna ricorrenza. Aggiungine una sopra!")
