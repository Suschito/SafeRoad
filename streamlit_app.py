import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import datetime

# Dati demo realistici per Trento
np.random.seed(42)
comuni = ['Trento', 'Rovereto', 'Pergine V.', 'Arco', 'Riva del Garda', 'Merano', 'Bolzano']
date = pd.date_range('2023-01-01', periods=36, freq='M')
data_list = []
for d in date:
    for comune in comuni:
        data_list.append({
            'data': d,
            'comune': comune,
            'incidenti': np.random.poisson(6 + comuni.index(comune), 1)[0],
            'feriti': np.random.poisson(10 + comuni.index(comune)*0.5, 1)[0],
            'morti': np.random.poisson(0.25, 1)[0]
        })
df = pd.DataFrame(data_list)
df['risk_score'] = np.minimum(100, df['incidenti']*0.4 + df['feriti']*0.3 + df['morti']*0.3)

st.set_page_config(layout="wide", page_title="SafeRoad")

# Header
st.title("🚗 SafeRoad")
st.markdown("**Road Accident Risk Dashboard** | Gruppo 7")

# Sidebar
st.sidebar.header("🔍 Filtri")
comune_sel = st.sidebar.selectbox("Comune:", ['Tutti'] + df['comune'].unique().tolist())
data_inizio = st.sidebar.date_input("Da:", datetime(2024,1,1))
data_fine = st.sidebar.date_input("A:", datetime(2025,12,31))

# Filtra
df_filtrato = df[(df['data'] >= pd.to_datetime(data_inizio)) & 
                 (df['data'] <= pd.to_datetime(data_fine))]
if comune_sel != 'Tutti':
    df_filtrato = df_filtrato[df_filtrato['comune'] == comune_sel]

# KPI
col1, col2, col3, col4 = st.columns(4)
col1.metric("📊 Incidenti", df_filtrato['incidenti'].sum())
col2.metric("🤕 Feriti", df_filtrato['feriti'].sum())
col3.metric("💀 Morti", df_filtrato['morti'].sum())
col4.metric("⚠️ Risk Score", f"{df_filtrato['risk_score'].mean():.0f}")

# Grafici
col_g1, col_g2 = st.columns(2)
with col_g1:
    trend = df_filtrato.groupby('data')['incidenti'].sum().reset_index()
    fig1 = px.line(trend, x='data', y='incidenti', title="Trend Incidenti")
    st.plotly_chart(fig1, use_container_width=True)

with col_g2:
    risk_ranking = df_filtrato.groupby('comune')['risk_score'].mean().sort_values(ascending=False)
    fig2 = px.bar(risk_ranking.reset_index(), x='risk_score', y='comune', 
                  orientation='h', title="Rischio per Comune")
    st.plotly_chart(fig2, use_container_width=True)

# Tabella
st.dataframe(df_filtrato[['comune', 'data', 'incidenti', 'feriti', 'morti', 'risk_score']])

# Download
csv = df.to_csv(index=False).encode('utf-8')
st.download_button("📥 Download CSV", csv, "saferoad.csv", "text/csv")

st.markdown("---")
st.caption("SafeRoad | Powered by Open Data Trentino | Gruppo 7")
