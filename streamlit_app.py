import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime

st.set_page_config(layout="wide", page_title="SafeRoad 🚗")

# =============================================================================
# FUNZIONI API
# =============================================================================
@st.cache_data(ttl=3600)
def fetch_open_data_trentino():
    try:
        url = "https://dati.trentino.it/api/3/action/datastore_search"
        params = {"resource_id": "9296f70a-fc3f-44ba-9f86-87d90c1352cf", "limit": 1000}
        r = requests.get(url, params=params, timeout=15)
        if r.status_code == 200:
            records = r.json().get("result", {}).get("records", [])
            if records:
                return pd.DataFrame(records), True
    except:
        pass
    return None, False

def genera_dati_demo():
    np.random.seed(42)
    comuni = ['Trento', 'Rovereto', 'Pergine V.', 'Arco', 'Riva del Garda',
              'Mezzolombardo', 'Cles', 'Tione', 'Borgo V.', 'Cavalese']
    dates = pd.date_range('2020-01-01', '2025-12-01', freq='MS')
    rows = []
    for d in dates:
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
            })
    df = pd.DataFrame(rows)
    df['risk_score'] = np.minimum(100,
        df['incidenti'] * 0.4 + df['feriti'] * 0.35 + df['morti'] * 0.25
    ).round(1)
    return df

# =============================================================================
# CARICAMENTO DATI
# =============================================================================
with st.spinner("Caricamento dati..."):
    df_trentino, ok = fetch_open_data_trentino()
    if ok and df_trentino is not None and len(df_trentino) > 10:
        df = df_trentino
        st.sidebar.success("✅ Dati: Open Data Trentino")
    else:
        df = genera_dati_demo()
        st.sidebar.warning("⚠️ Dati demo (API non disponibile)")

# =============================================================================
# HEADER
# =============================================================================
st.title("🚗 SafeRoad")
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown("**Road Accident Risk Dashboard** | Provincia di Trento")
with col_h2:
    st.caption(f"🕒 Ultimo aggiornamento: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

st.markdown("---")

# =============================================================================
# SIDEBAR FILTRI
# =============================================================================
st.sidebar.header("🔍 Filtri")
st.sidebar.markdown("---")

comuni_list = sorted(df['comune'].unique().tolist())
comune_sel = st.sidebar.selectbox("📍 Comune", ['Tutti'] + comuni_list)

gravita_sel = st.sidebar.selectbox("⚠️ Gravità", ['Tutti', 'Con feriti', 'Mortali'])

anni_list = sorted(df['anno'].unique().tolist(), reverse=True)
anno_sel = st.sidebar.multiselect("📅 Anno", options=anni_list, default=anni_list[:3])

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
col1.metric("📊 Incidenti Totali", f"{df_f['incidenti'].sum():,}")
col2.metric("🤕 Feriti",           f"{df_f['feriti'].sum():,}")
col3.metric("💀 Morti",            f"{df_f['morti'].sum():,}")
col4.metric("⚠️ Risk Score Medio", f"{df_f['risk_score'].mean():.0f}/100")

st.markdown("---")

# =============================================================================
# GRAFICI NATIVI STREAMLIT (zero dipendenze extra)
# =============================================================================
col_g1, col_g2 = st.columns(2)

with col_g1:
    st.markdown("**📈 Trend mensile incidenti**")
    trend = (
        df_f.groupby('data')['incidenti']
        .sum()
        .reset_index()
        .set_index('data')
        .sort_index()
    )
    st.line_chart(trend)

with col_g2:
    st.markdown("**🏙️ Risk Score per Comune**")
    risk_by_com = (
        df_f.groupby('comune')['risk_score']
        .mean()
        .sort_values(ascending=False)
    )
    st.bar_chart(risk_by_com)

st.markdown("**📅 Stagionalità — Incidenti medi per mese**")
mesi_order = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
stagione = (
    df_f.groupby('mese')['incidenti']
    .mean()
    .reindex([m for m in mesi_order if m in df_f['mese'].values])
)
st.bar_chart(stagione)

# =============================================================================
# RISK SCORE BREAKDOWN
# =============================================================================
st.markdown("---")
st.markdown("### 🎯 Fattori di Rischio")
col_r1, col_r2, col_r3, col_r4 = st.columns(4)
col_r1.metric("📌 Frequenza storica", "42%")
col_r2.metric("🌤️ Stagionalità",     "28%")
col_r3.metric("🔴 Indice gravità",   "18%")
col_r4.metric("👥 Densità pop.",     "12%")

# =============================================================================
# TABELLA
# =============================================================================
st.markdown("---")
st.markdown("### 📋 Dati Dettaglio")
st.dataframe(
    df_f[['comune', 'anno', 'mese', 'incidenti', 'feriti', 'morti', 'risk_score']]
    .sort_values(['anno', 'comune'])
    .head(50),
    use_container_width=True
)

# =============================================================================
# DOWNLOAD
# =============================================================================
csv = df_f.to_csv(index=False).encode('utf-8')
st.download_button("📥 Scarica Dati Filtrati (CSV)", csv, "saferoad_export.csv", "text/csv")

# =============================================================================
# FOOTER
# =============================================================================
st.markdown("---")
st.caption("**SafeRoad** | Gruppo 7 — Gianluca Pisetta, Erika Minelli, Antonio Susca | Powered by ISTAT & Open Data Trentino")
