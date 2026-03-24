import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

# =============================================================================
# DATI DEMO (sostituisci con dati reali da Open Data Trentino)
# =============================================================================
np.random.seed(42)
municipalities = ['Trento', 'Rovereto', 'Pergine Valsugana', 'Arco', 'Riva del Garda', 'Merano', 'Bolzano', 'Bressanone', 'Brunico', 'Bassano del Grappa']
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

# =============================================================================
# DASHBOARD SAFE ROAD
# =============================================================================
st.set_page_config(page_title="SafeRoad", page_icon="🚗", layout="wide")

st.title("🚗 SafeRoad - Road Accident Risk Dashboard")
st.markdown("**Insurance Risk Intelligence Platform** | Powered by ISTAT & Open Data Trentino")

# Sidebar con filtri
st.sidebar.header("🔍 **Filtri**")
selected_municipality = st.sidebar.selectbox(
    "Comune",
    options=['Tutti'] + sorted(df['comune'].unique().tolist()),
    index=0
)
period_start = st.sidebar.date_input("Data inizio", value=datetime(2024, 1, 1))
period_end = st.sidebar.date_input("Data fine", value=datetime(2025, 12, 31))
severity = st.sidebar.selectbox("Gravità", ['Tutti', 'Con feriti', 'Mortali'])

# Filtra i dati
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

# =============================================================================
# KPI CARDS
# =============================================================================
col1, col2, col3, col4 = st.columns(4, gap="medium")
with col1:
    st.metric("📊 Incidenti totali", f"{filtered_df['incidenti'].sum():,}", delta="↗ 2.1%")
with col2:
    st.metric("🤕 Feriti", f"{filtered_df['feriti'].sum():,}", delta="↗ 1.8%")
with col3:
    st.metric("💀 Morti", f"{filtered_df['morti'].sum():,}", delta="↘ 0.3%")
with col4:
    avg_risk = filtered_df['risk_score'].mean()
    st.metric("⚠️ Risk Score", f"{avg_risk:.0f}/100", delta=f"Δ {avg_risk-50:+.1f}")

# =============================================================================
# MAPPA + RISK SCORE
# =============================================================================
st.markdown("### 🎯 **Valutazione Rischio Corrente**")
col_map, col_risk = st.columns([2, 1])

with col_map:
    # Heatmap comuni
    map_data = filtered_df.groupby('comune').agg({
        'risk_score':'mean', 
        'incidenti':'sum'
    }).reset_index()
    fig_map = px.choropleth(
        map_data,
        locations='comune',
        color='risk_score',
        locationmode='country names',
        color_continuous_scale='RdYlGn_r',
        title="Rischio per Comune",
        labels={'risk_score': 'Risk Score'}
    )
    fig_map.update_layout(height=400)
    st.plotly_chart(fig_map, use_container_width=True)

with col_risk:
    st.markdown("**Fattori di rischio**")
    risk_factors = {
        "Frequenza storica": "42%",
        "Stagionalità": "28%", 
        "Indice gravità": "18%",
        "Densità popolazione": "12%"
    }
    for factor, weight in risk_factors.items():
        col_a, col_b = st.columns([3,1])
        with col_a:
            st.caption(f"• {factor}")
        with col_b:
            st.caption(weight)

# =============================================================================
# GRAFICI ANALISI
# =============================================================================
st.markdown("### 📊 **Analisi Dettagliata**")
col1, col2 = st.columns(2)

with col1:
    # Trend temporale
    trend_data = filtered_df.groupby('data')['incidenti'].sum().reset_index()
    fig_trend = px.line(trend_data, x='data', y='incidenti', 
                       title="Trend Incidenti nel Tempo")
    st.plotly_chart(fig_trend, use_container_width=True)

with col2:
    # Ranking comuni più rischiosi
    ranking_data = filtered_df.groupby('comune')['risk_score'].mean().sort_values(ascending=False).reset_index().head(10)
    fig_ranking = px.bar(ranking_data, x='risk_score', y='comune',
                        orientation='h',
                        title="Comuni più a rischio",
                        color='risk_score',
                        color_continuous_scale='RdYlGn_r')
    st.plotly_chart(fig_ranking, use_container_width=True)

# =============================================================================
# TABELLA DETTAGLI
# =============================================================================
st.markdown("### 📋 **Dettaglio Incidenti**")
st.dataframe(
    filtered_df[['comune', 'data', 'incidenti', 'feriti', 'morti', 'risk_score']]
    .head(20)
    .style.format({
        'incidenti': '{:.0f}',
        'feriti': '{:.0f}', 
        'morti': '{:.0f}',
        'risk_score': '{:.1f}'
    }),
    use_container_width=True
)

# =============================================================================
# DOWNLOAD DATI
# =============================================================================
st.sidebar.markdown("---")
csv = df.to_csv(index=False).encode('utf-8')
st.sidebar.download_button(
    label="📥 Scarica Dataset Completo",
    data=csv,
    file_name='saferoad_incidenti_trentino.csv',
    mime='text/csv'
)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
**SafeRoad** | Powered by ISTAT e Open Data Trentino<br>
Last update: 24 Mar 2026 | Gruppo 7 Project
</div>
""")
