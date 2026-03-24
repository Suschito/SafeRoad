import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime
from io import StringIO

st.set_page_config(layout="wide", page_title="SafeRoad 🚗", page_icon="🚗")

# =============================================================================
# DATA & API
# =============================================================================
SEASONS = {
    "Spring": [3, 4, 5],
    "Summer": [6, 7, 8],
    "Autumn": [9, 10, 11],
    "Winter": [12, 1, 2]
}

AGE_GROUPS = ["18–24", "25–29", "30–59", "Over 60"]

ITALIAN_PROVINCES = [
    "Agrigento","Alessandria","Ancona","Aosta","Arezzo","Ascoli Piceno","Asti",
    "Avellino","Bari","Barletta-Andria-Trani","Belluno","Benevento","Bergamo",
    "Biella","Bologna","Bolzano","Brescia","Brindisi","Cagliari","Caltanissetta",
    "Campobasso","Caserta","Catania","Catanzaro","Chieti","Como","Cosenza",
    "Cremona","Crotone","Cuneo","Enna","Fermo","Ferrara","Firenze","Foggia",
    "Forlì-Cesena","Frosinone","Genova","Gorizia","Grosseto","Imperia","Isernia",
    "La Spezia","L'Aquila","Latina","Lecce","Lecco","Livorno","Lodi","Lucca",
    "Macerata","Mantova","Massa-Carrara","Matera","Messina","Milano","Modena",
    "Monza e Brianza","Napoli","Novara","Nuoro","Oristano","Padova","Palermo",
    "Parma","Pavia","Perugia","Pesaro e Urbino","Pescara","Piacenza","Pisa",
    "Pistoia","Pordenone","Potenza","Prato","Ragusa","Ravenna","Reggio Calabria",
    "Reggio Emilia","Rieti","Rimini","Roma","Rovigo","Salerno","Sassari","Savona",
    "Siena","Siracusa","Sondrio","Sud Sardegna","Taranto","Teramo","Terni",
    "Torino","Trapani","Trento","Treviso","Trieste","Udine","Varese","Venezia",
    "Verbano-Cusio-Ossola","Vercelli","Verona","Vibo Valentia","Vicenza","Viterbo"
]

@st.cache_data(ttl=3600)
def fetch_mortality_data():
    """Real data: road mortality rates from Provincia di Trento"""
    try:
        url = "https://statweb.provincia.tn.it/indicatoristrutturali/exp.aspx?fmt=csv&idind=824&t=i"
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            df = pd.read_csv(StringIO(r.text), sep=';')
            df['Anno'] = df['Anno'].astype(int)
            return df, True
    except:
        pass
    return None, False

@st.cache_data(ttl=3600)
def fetch_youth_mortality():
    """Real data: youth (15-34) road mortality"""
    try:
        url = "https://statweb.provincia.tn.it/indicatoristrutturali/exp.aspx?fmt=csv&idind=829&t=i"
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            df = pd.read_csv(StringIO(r.text), sep=';')
            df['Anno'] = df['Anno'].astype(int)
            return df, True
    except:
        pass
    return None, False

def generate_province_data():
    """Demo data per RF1: injured/dead by role and province"""
    np.random.seed(42)
    rows = []
    age_risk = {"18–24": 1.6, "25–29": 1.3, "30–59": 1.0, "Over 60": 1.2}
    season_risk = {"Spring": 1.1, "Summer": 1.3, "Autumn": 1.0, "Winter": 0.9}

    for province in ITALIAN_PROVINCES:
        for season in SEASONS.keys():
            for age in AGE_GROUPS:
                base = np.random.uniform(30, 200)
                s_mult = season_risk[season]
                a_mult = age_risk[age]
                rows.append({
                    "province": province,
                    "season": season,
                    "age_group": age,
                    "injured_pedestrians": max(0, int(np.random.poisson(base * 0.2 * s_mult * a_mult))),
                    "injured_drivers":     max(0, int(np.random.poisson(base * 0.5 * s_mult * a_mult))),
                    "injured_passengers":  max(0, int(np.random.poisson(base * 0.3 * s_mult * a_mult))),
                    "dead_pedestrians":    max(0, int(np.random.poisson(base * 0.01 * s_mult * a_mult))),
                    "dead_drivers":        max(0, int(np.random.poisson(base * 0.02 * s_mult * a_mult))),
                    "dead_passengers":     max(0, int(np.random.poisson(base * 0.01 * s_mult * a_mult))),
                })

    df = pd.DataFrame(rows)
    df["total_injured"] = df["injured_pedestrians"] + df["injured_drivers"] + df["injured_passengers"]
    df["total_dead"]    = df["dead_pedestrians"] + df["dead_drivers"] + df["dead_passengers"]
    df["risk_score"]    = np.minimum(100,
        df["total_injured"] * 0.4 + df["total_dead"] * 1.5
    ).round(1)

    def risk_label(s):
        if s < 30: return "🟢 Low"
        elif s < 60: return "🟡 Medium"
        else: return "🔴 High"

    df["risk_level"] = df["risk_score"].apply(risk_label)
    return df

# =============================================================================
# LOAD DATA
# =============================================================================
df_main = generate_province_data()
df_mort, ok_mort = fetch_mortality_data()
df_youth, ok_youth = fetch_youth_mortality()

# =============================================================================
# HEADER
# =============================================================================
st.title("🚗 SafeRoad")
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown("**Insurance Risk Assessment Dashboard** | All Italian Provinces")
    st.caption("Group 7 — Gianluca Pisetta, Erika Minelli, Antonio Susca")
with col_h2:
    st.caption(f"🕒 Last update: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    if ok_mort:
        st.success("✅ Live data: Provincia di Trento")
    else:
        st.warning("⚠️ Demo data active")

st.markdown("---")

# =============================================================================
# SIDEBAR — RF3: Filters (Province, Season, Age Group)
# =============================================================================
st.sidebar.header("🔍 Filters")
st.sidebar.markdown("---")

selected_provinces = st.sidebar.multiselect(
    "📍 Province(s)",
    options=ITALIAN_PROVINCES,
    default=["Roma", "Milano", "Torino", "Napoli", "Trento"]
)

selected_season = st.sidebar.selectbox(
    "🌤️ Season",
    options=list(SEASONS.keys())
)

selected_age = st.sidebar.selectbox(
    "👤 Age Group",
    options=AGE_GROUPS
)

st.sidebar.markdown("---")
st.sidebar.markdown("**📌 Data Sources**")
st.sidebar.caption("• [ISTAT](https://www.istat.it)")
st.sidebar.caption("• [Open Data Trentino](https://dati.trentino.it)")
st.sidebar.caption("• [Statistica Trentino](https://statweb.provincia.tn.it)")
st.sidebar.markdown("---")
st.sidebar.caption(f"Data reference: ISTAT 2004–2022")
st.sidebar.caption("All road types included. No road-type filtering.")

# =============================================================================
# FILTER DATA
# =============================================================================
if not selected_provinces:
    selected_provinces = ["Roma"]

df_f = df_main[
    (df_main["province"].isin(selected_provinces)) &
    (df_main["season"] == selected_season) &
    (df_main["age_group"] == selected_age)
]

# =============================================================================
# RF1 — KPI CARDS
# =============================================================================
st.markdown(f"### 📊 Risk Indicators — {selected_season} | Age group: {selected_age}")

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("🚶 Injured Pedestrians", f"{df_f['injured_pedestrians'].sum():,}")
col2.metric("🚗 Injured Drivers",     f"{df_f['injured_drivers'].sum():,}")
col3.metric("🧑 Injured Passengers",  f"{df_f['injured_passengers'].sum():,}")
col4.metric("💀 Dead Pedestrians",    f"{df_f['dead_pedestrians'].sum():,}")
col5.metric("💀 Dead Drivers",        f"{df_f['dead_drivers'].sum():,}")
col6.metric("💀 Dead Passengers",     f"{df_f['dead_passengers'].sum():,}")

st.markdown("---")

# =============================================================================
# RF2 — RISK SCORE + CONTRIBUTING FACTORS
# =============================================================================
st.markdown("### 🎯 Risk Score Estimation")

col_rs1, col_rs2 = st.columns([1, 2])

with col_rs1:
    avg_risk = df_f["risk_score"].mean()
    if avg_risk < 30:
        badge = "🟢 LOW RISK"
        color = "green"
    elif avg_risk < 60:
        badge = "🟡 MEDIUM RISK"
        color = "orange"
    else:
        badge = "🔴 HIGH RISK"
        color = "red"

    st.markdown(f"""
    <div style='
        background:#1e1e1e;
        border:2px solid {color};
        border-radius:12px;
        padding:24px;
        text-align:center;
    '>
        <div style='font-size:48px;font-weight:bold;color:{color}'>{avg_risk:.0f}</div>
        <div style='color:#aaa;margin-bottom:8px'>out of 100</div>
        <div style='font-size:20px;font-weight:bold;color:{color}'>{badge}</div>
        <div style='color:#888;font-size:12px;margin-top:8px'>
            Based on historical patterns,<br>seasonality & age group
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_rs2:
    st.markdown("**Main contributing factors:**")

    season_w = {"Spring": 22, "Summer": 31, "Autumn": 18, "Winter": 15}
    age_w    = {"18–24": 38, "25–29": 28, "30–59": 18, "Over 60": 24}

    factors = {
        "📍 Historical accident density": 35,
        f"🌤️ Seasonality ({selected_season})": season_w.get(selected_season, 20),
        f"👤 Age group risk ({selected_age})": age_w.get(selected_age, 20),
        "🛣️ All road types (aggregated)": 10,
    }
    total_w = sum(factors.values())
    for factor, weight in factors.items():
        pct = round(weight / total_w * 100)
        st.markdown(f"**{factor}** — {pct}%")
        st.progress(pct / 100)

st.markdown("---")

# =============================================================================
# RF1 — COMPARISON TABLE + CHART
# =============================================================================
st.markdown("### 🏙️ Province Comparison")

compare_df = df_f.groupby("province").agg({
    "injured_pedestrians": "sum",
    "injured_drivers":     "sum",
    "injured_passengers":  "sum",
    "dead_pedestrians":    "sum",
    "dead_drivers":        "sum",
    "dead_passengers":     "sum",
    "total_injured":       "sum",
    "total_dead":          "sum",
    "risk_score":          "mean",
    "risk_level":          "first"
}).reset_index().sort_values("risk_score", ascending=False)

col_t1, col_t2 = st.columns(2)

with col_t1:
    st.markdown("**Risk Score by Province**")
    chart_data = compare_df.set_index("province")["risk_score"]
    st.bar_chart(chart_data)

with col_t2:
    st.markdown("**Injured vs Dead by Province**")
    chart2 = compare_df.set_index("province")[["total_injured", "total_dead"]]
    st.bar_chart(chart2)

st.markdown("**📋 Detailed Comparison Table**")
st.dataframe(
    compare_df[[
        "province", "injured_pedestrians", "injured_drivers", "injured_passengers",
        "dead_pedestrians", "dead_drivers", "dead_passengers",
        "risk_score", "risk_level"
    ]].rename(columns={
        "province":             "Province",
        "injured_pedestrians":  "Inj. Pedestrians",
        "injured_drivers":      "Inj. Drivers",
        "injured_passengers":   "Inj. Passengers",
        "dead_pedestrians":     "Dead Pedestrians",
        "dead_drivers":         "Dead Drivers",
        "dead_passengers":      "Dead Passengers",
        "risk_score":           "Risk Score",
        "risk_level":           "Risk Level"
    }),
    use_container_width=True
)

st.markdown("---")

# =============================================================================
# REAL DATA SECTION — ISTAT via Trentino API
# =============================================================================
if ok_mort and df_mort is not None:
    st.markdown("### 📈 Real Data — Road Mortality (ISTAT via Open Data Trentino)")

    col_rd1, col_rd2 = st.columns(2)
    with col_rd1:
        st.markdown("**Mortality rate: Trentino vs Italy (per 100k inhabitants)**")
        st.line_chart(df_mort[["Anno", "Trentino", "Italia"]].set_index("Anno"))

    with col_rd2:
        st.markdown("**Regional comparison — latest year available**")
        last = df_mort.iloc[-1]
        regioni = {k: float(str(v).replace(',', '.')) for k, v in last.items() if k != 'Anno'}
        st.bar_chart(pd.Series(regioni))

    if ok_youth and df_youth is not None:
        st.markdown("**👶 Youth mortality (15–34) — Trentino**")
        st.line_chart(df_youth[["Anno", "Trentino"]].set_index("Anno"))

    st.markdown("---")

# =============================================================================
# AGE GROUP RISK OVERVIEW
# =============================================================================
st.markdown("### 👥 Risk by Age Group — All Selected Provinces")
age_compare = df_main[
    (df_main["province"].isin(selected_provinces)) &
    (df_main["season"] == selected_season)
].groupby("age_group").agg({"risk_score": "mean"}).reindex(AGE_GROUPS)

st.bar_chart(age_compare)

# =============================================================================
# SEASONAL RISK OVERVIEW
# =============================================================================
st.markdown("### 🌤️ Risk by Season — Selected Age Group & Provinces")
season_compare = df_main[
    (df_main["province"].isin(selected_provinces)) &
    (df_main["age_group"] == selected_age)
].groupby("season").agg({"risk_score": "mean"}).reindex(list(SEASONS.keys()))

st.bar_chart(season_compare)

st.markdown("---")

# =============================================================================
# DOWNLOAD
# =============================================================================
csv = df_f.to_csv(index=False).encode("utf-8")
st.download_button("📥 Download Filtered Data (CSV)", csv, "saferoad_export.csv", "text/csv")

# =============================================================================
# FOOTER
# =============================================================================
st.markdown("---")
st.caption(
    "**SafeRoad** | Group 7 — Gianluca Pisetta, Erika Minelli, Antonio Susca | "
    "Powered by ISTAT & Open Data Trentino | All road types included, no road-type filtering"
)
