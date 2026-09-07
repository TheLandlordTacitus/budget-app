# --- ANALISI PER TIPO ---
st.divider()
st.subheader("📊 Analisi per Tipo (personalizzato)")

# Spese - grafico a torta
spese_df = df[df["Importo"] < 0]
if not spese_df.empty:
    spese_tipo = spese_df.groupby("Tipo")["Importo"].sum().abs().reset_index()
    
    col1, col2 = st.columns(2)
    with col1:
        # Grafico a torta per le spese
        fig_spese_pie = px.pie(spese_tipo, values="Importo", names="Tipo",
                               title="Spese per Tipo (%)",
                               hole=0.3, color_discrete_sequence=px.colors.sequential.Reds_r)
        st.plotly_chart(fig_spese_pie, use_container_width=True)
    with col2:
        # Grafico a barre per le spese (come prima)
        fig_spese_bar = px.bar(spese_tipo, x="Tipo", y="Importo",
                               title="Spese per Tipo (€)",
                               color="Tipo", text_auto=True)
        st.plotly_chart(fig_spese_bar, use_container_width=True)
else:
    st.info("Nessuna spesa registrata.")

# Entrate - grafico a torta (come prima)
entrate_df = df[df["Importo"] > 0]
if not entrate_df.empty:
    entrate_tipo = entrate_df.groupby("Tipo")["Importo"].sum().reset_index()
    fig_entrate_tipo = px.pie(entrate_tipo, values="Importo", names="Tipo",
                              title="Entrate per Tipo (%)",
                              hole=0.3)
    st.plotly_chart(fig_entrate_tipo, use_container_width=True)
else:
    st.info("Nessuna entrata registrata.")
