import streamlit as st
import pandas as pd
import numpy as np
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

st.set_page_config(layout="wide", page_title="SafeRoad 🚗")

# =============================================================================
# FUNZIONI API ISTAT SDMX
# =============================================================================
SDMX_BASE = "https://sdmx.istat.it/SDMXWS/rest"

@st.cache_data(ttl=3600)
def fetch_istat_accidents():
    """Scarica dati incidenti stradali da API ISTAT SDMX"""
    try:
        # Dataset: morti e feriti stradali per regione e anno
        url = f"{SDMX_BASE}/data/41_270_DF_DCIS_MORTIFERITISTR1_1/A.....?startPeriod=2018&endPeriod=2023&format=csv"
        r = requests.get(url, timeout=20)
        if r.status_code == 200:
            from io import StringIO
            df = pd.read_csv(StringIO(r.text))
            return df, True
    except Exception as e:
        pass
    return None, False

@st.cache_data(ttl=3600)
def fetch_istat_sdmx_xml():
    """Fallback: scarica dati ISTAT in formato SDMX-ML"""
    try:
        url = f"{SDMX_BASE}/data/DCIS_INCIDMORFER_COM/A.....?startPeriod=2015&endPeriod=2023"
        r = requests.get(url, timeout=20, headers={
            "Accept": "application/vnd.sdmx.genericdata+xml;version=2.1"
        })
        if r.status_code == 200:
            return r.text, True
    except:
        pass
    return None, False

@st.cache_data(ttl=3600)
def fetch_open_data_trentino():
    """Scarica dati incidenti stradali da Open Data Trentino via CKAN API"""
    try:
        url = "https://dati.trentino.it/api/3/action/datastore_search"
        params = {
            "resource_id": "9296f70a-fc3f-44ba-9f86-87d90c1352cf",
            "limit": 1000
        }
        r = requests.get(url, params=params, timeout=15)
        if r.status_code == 200:
            records = r.json().get("result", {}).get("records", [])
            if records:
                return pd.DataFrame(records), True
    except:
        pass
    return None, False

def genera_dati_demo():
    """Dati demo realistici per la Provincia di Trento (fallback)"""
    np.random.seed(42)
    comuni = ['Trento', 'Rovereto', 'Pergine V.', 'Arco', 'Riva del Garda',
              'Mezzolombardo', 'Cles', 'Tione', 'Borgo V.', 'Cavalese']
    dates = pd.date_range('2020-01-01', '2025-12-01', freq='MS')
    rows = []
    for d in dates:
        # stagionalità: estate più incidenti
        stagione = 1 + 0.3 * np.sin((d.month - 6) * np.pi / 6)
        for i, c in enumerate(comuni):
            base = 4 + i * 0.5
            rows.append({
                'data': d,
                'anno': d.year,
                'mese': d.strftime('%b'),
                'comune': c,
                'incidenti': max(0, int(np.random.poisson(base * stagione))),
                'feriti': max(0, int(np.random.poisson((base + 3) * stagione))),
                'morti': max(0, int(np.random.poisson(0.25))),
                'fonte': 'Demo (ISTAT/Open Data Trentino)'
            })
    df = pd.DataFrame(rows)
    df['risk_score'] = np.minimum(100,
        df['incidenti'] * 0.4 + df['feriti'] * 0.35 + df['morti'] * 0.25
    ).round(1)
    return df

# =============================================================================
# CARICAMENTO DATI
# =============================================================================
with st.spinner("Caricamento dati ISTAT..."):
    df_trentino, ok_trentino = fetch_open_data_trentino()
    if ok_trentino and df_trentino is not None and len(df_trentino) > 10:
        st.sidebar.success("✅ Dati: Open Data Trentino")
        df = df_trentino
    else:
        df = genera_dati_demo()
        st.sidebar.warning("⚠️ Dati demo (API non disponibile)")

# =============================================================================
# HEADER
# =============================================================================
st.title("🚗 SafeRoad")
col_h1, col_h2 = st.columns([3,1])
with col_h1:
    st.markdown("**Road Accident Risk Dashboard** | Provincia di Trento")
with col_h2:
    st.caption(f"🕒 Ultimo aggiornamento: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

st.markdown("---")

# =============================================================================
# SIDEBAR FILTRI (solo comune + gravità, NO date picker)
# =============================================================================
st.sidebar.header("🔍 Filtri")
st.sidebar.markdown("---")

comuni_list = sorted(df['comune'].unique().tolist())
comune_sel = st.sidebar.selectbox("📍 Comune", ['Tutti'] + comuni_list)

gravita_sel = st.sidebar.selectbox(
    "⚠️ Gravità",
    ['Tutti', 'Con feriti', 'Mortali']
)

anni_list = sorted(df['anno'].unique().tolist(), reverse=True)
anno_sel = st.sidebar.multiselect(
    "📅 Anno",
    options=anni_list,
    default=anni_list[:3]
)

st.sidebar.markdown("---")
st.sidebar.markdown("**📌 Fonte dati**")
st.sidebar.caption("• [ISTAT](https://www.istat.it)")
st.sidebar.caption("• [Open Data Trentino](https://dati.trentino.it)")

# =============================================================================
# FILTRAGGIO
# =============================================================================
df_f = df.copy()

if anno_sel:
    df_f = df_f[df_f['anno'].isin(anno_sel)]

if comune_sel != 'Tutti':
    df_f = df_f[df_f['comune'] == comune_sel]

if gravita_sel == 'Mortali':
    df_f = df_f[df_f['morti'] > 0]
elif gravita_sel == 'Con feriti':
    df_f = df_f[df_f['feriti'] > 0]

# =============================================================================
# KPI CARDS
# =============================================================================
col1, col2, col3, col4 = st.columns(4)
total_inc = df_f['incidenti'].sum()
total_fer = df_f['feriti'].sum()
total_mor = df_f['morti'].sum()
avg_risk  = df_f['risk_score'].mean()

col1.metric("📊 Incidenti Totali", f"{total_inc:,}")
col2.metric("🤕 Feriti",           f"{total_fer:,}")
col3.metric("💀 Morti",            f"{total_mor:,}")
col4.metric("⚠️ Risk Score Medio", f"{avg_risk:.0f}/100")

st.markdown("---")

# =============================================================================
# GRAFICI (matplotlib, no plotly)
# =============================================================================
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

col_g1, col_g2 = st.columns(2)

with col_g1:
    st.markdown("**📈 Trend mensile incidenti**")
    trend = df_f.groupby('data')['incidenti'].sum().reset_index().sort_values('data')
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.plot(trend['data'], trend['incidenti'], color='#1f77b4', linewidth=2)
    ax.fill_between(trend['data'], trend['incidenti'], alpha=0.2, color='#1f77b4')
    ax.set_xlabel("Mese")
    ax.set_ylabel("Incidenti")
    ax.xaxis.set_major_locator(ticker.AutoLocator())
    plt.xticks(rotation=45, fontsize=7)
    plt.tight_layout()
    st.pyplot(fig)

with col_g2:
    st.markdown("**🏙️ Rischio per Comune**")
    risk_by_com = df_f.groupby('comune')['risk_score'].mean().sort_values(ascending=True)
    colors = ['#d62728' if v > 7 else '#ff7f0e' if v > 4 else '#2ca02c' for v in risk_by_com.values]
    fig2, ax2 = plt.subplots(figsize=(6, 3))
    ax2.barh(risk_by_com.index, risk_by_com.values, color=colors)
    ax2.set_xlabel("Risk Score medio")
    plt.tight_layout()
    st.pyplot(fig2)

# Grafico stagionalità
st.markdown("**📅 Distribuzione mensile incidenti**")
mesi_order = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
stagione = df_f.groupby('mese')['incidenti'].mean().reindex(
    [m for m in mesi_order if m in df_f['mese'].unique()]
)
fig3, ax3 = plt.subplots(figsize=(10, 2.5))
ax3.bar(stagione.index, stagione.values, color='#1f77b4')
ax3.set_ylabel("Incidenti medi")
ax3.set_title("Stagionalità")
plt.tight_layout()
st.pyplot(fig3)

# =============================================================================
# TABELLA
# =============================================================================
st.markdown("---")
st.markdown("### 📋 Dati Dettaglio")
st.dataframe(
    df_f[['comune','anno','mese','incidenti','feriti','morti','risk_score']]
    .sort_values(['anno','mese'], ascending=[False,True])
    .head(50),
    use_container_width=True
)

# =============================================================================
# DOWNLOAD
# =============================================================================
csv = df_f.to_csv(index=False).encode('utf-8')
st.download_button("📥 Scarica Dati Filtrati (CSV)", csv, "saferoad_export.csv", "text/csv")

st.markdown("---")
st.caption("**SafeRoad** | Gruppo 7 — Gianluca Pisetta, Erika Minelli, Antonio Susca | Powered by ISTAT & Open Data Trentino")
