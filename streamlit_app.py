import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

# Genera dati demo realistici (sostituisci con dati reali da Open Data Trentino)
np.random.seed(42)
municipalities = ['Trento', 'Rovereto', 'Pergine Valsugana', 'Arco', 'Riva del Garda', 
                 'Merano', 'Bolzano', 'Bressanone', 'Brunico', 'Bassano del Grappa']
dates = pd.date_range(start='2023-01-01', end='2025-12-31', freq='M')
data = []
for month in dates:
    for mun in municipalities:
        data.append({
            'data': month,
            'comune': mun,
            'incidenti': np.random.poisson(5 + municipalities.index(mun)/2, 1)[0],
            'feriti': np.random.poisson(8 + municipalities.index(mun), 1)[0],
            'morti': np.random.poisson(0.2, 1)[0],
            'popolazione': np.random.randint(10000, 80000, 1)[0]
        })
df = pd.DataFrame(data)
df['tasso_incidenti'] = df['incidenti'] / (df['popolazione'] / 1000000)
df['risk_score'] = (df['incidenti'] * 0.4 + df['feriti'] * 0.3 + df['morti'] * 0.3).clip(0, 100)

# Configurazione pagina
st.set_page_config(page_title="SafeRoad", page_icon="🚗", layout="wide")

# Header
st.title("🚗 SafeRoad - Road Accident Risk Dashboard")
st.markdown("**Insurance Risk Intelligence Platform** | Powered by ISTAT & Open Data Trentino")

# Sidebar filtri
st.sidebar.header("🔍 **Filtri**")
selected_municipality = st.sidebar.selectbox(
    "Comune",
    options=['Tutti'] + sorted(df['comune'].unique().tolist())
)
period_start = st.sidebar.date_input("Inizio periodo", value=datetime(2024, 1, 1))
period_end = st.sidebar.date_input("Fine periodo", value=datetime(2025, 12, 31))
severity = st.sidebar.selectbox("Gravità", ['Tutti', 'Con feriti', 'Mortali'])

# Filtra dati
filtered_df = df[
    (df['data'].dt.date >= period_start) & 
    (df['data'].dt.date <= period_end)
]
if selected_municipality != 'Tutti':
    filtered_df = filtered_df[filtered_df['comune'] == selected_municipality]
if severity == 'Mortali':
    filtered_df = filtered_df[filtered_df['morti'] > 0]
elif severity == 'Con feriti':
    filtered_df = filtered_df[filtered_df['feriti'] > 0]

# KPI Cards
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("📊 Incidenti", f"{filtered_df['incidenti'].sum():,}")
with col2:
    st.metric("🤕 Feriti", f"{filtered_df['feriti'].sum():,}")
with col3:
    st.metric("💀 Morti", f"{filtered_df['morti'].sum():,}")
with col4:
    avg_risk = filtered_df['risk_score'].mean()
    color = "normal" if avg_risk < 50 else "inverse"
    st.metric("⚠️ Risk Score", f"{avg_risk:.0f}/100", delta=f"Δ{avg_risk-50:+.0f}", delta_color="normal")

# Map + Risk Breakdown
st.markdown("### 🎯 **Valutazione Rischio**")
col_map, col_risk = st.columns([2, 1])

with col_map:
    map_data = filtered_df.groupby('comune').agg({'risk_score':'mean'}).reset_index()
    fig_map = px.scatter(map_data, x='comune', y='risk_score', 
                        size='risk_score', color='risk_score',
                        title="Rischio per Comune",
                        color_continuous_scale='RdYlGn_r')
    fig_map.update_layout(height=350)
    st.plotly_chart(fig_map, use_container_width=True)

with col_risk:
    st.markdown("**Fattori principali**")
    factors = ["Frequenza storica", "Stagionalità", "Gravità", "Densità"]
    weights = [42, 28, 18, 12]
    for f, w in zip(factors, weights):
        col_a, col_b = st.columns([3,1])
        with col_a:
            st.caption(f"• {f}")
        with col_b:
            st.caption(f"{w}%")

# Grafici
st.markdown("### 📊 **Analisi**")
col1, col2 = st.columns(2)
with col1:
    trend_data = filtered_df.groupby('data')['incidenti'].sum().reset_index()
    fig_trend = px.line(trend_data, x='data', y='incidenti', title="Trend Incidenti")
    st.plotly_chart(fig_trend, use_container_width=True)

with col2:
    ranking_data = filtered_df.groupby('comune')['risk_score'].mean().sort_values(ascending=False).head(10)
    fig_ranking = px.bar(ranking_data.reset_index(), x='risk_score', y='comune', 
                        orientation='h', title="Top 10 Comuni a Rischio",
                        color='risk_score', color_continuous_scale='RdYlGn_r')
    st.plotly_chart(fig_ranking, use_container_width=True)

# Tabella
st.markdown("### 📋 **Dati Dettaglio**")
st.dataframe(filtered_df[['comune', 'data', 'incidenti', 'feriti', 'morti', 'risk_score']].head(20))

# Download
csv = df.to_csv(index=False).encode('utf-8')
st.sidebar.download_button(
    "📥 Scarica CSV",
    csv,
    "saferoad_dati_trentino.csv",
    "text/csv"
)

# Footer
st.markdown("---")
st.markdown("*SafeRoad | Gruppo 7 | Powered by ISTAT & Open Data Trentino*")
