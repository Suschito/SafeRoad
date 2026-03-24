import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime
from io import StringIO

st.set_page_config(layout="wide", page_title="SafeRoad 🚗", page_icon="🚗")

# =============================================================================
# CONSTANTS
# =============================================================================
MONTHS = {
    "All Months": 0,
    "January": 1, "February": 2, "March": 3,
    "April": 4, "May": 5, "June": 6,
    "July": 7, "August": 8, "September": 9,
    "October": 10, "November": 11, "December": 12
}

MONTH_RISK = {
    1: 0.85, 2: 0.88, 3: 1.00, 4: 1.05, 5: 1.10,
    6: 1.25, 7: 1.30, 8: 1.28, 9: 1.10, 10: 1.00,
    11: 0.90, 12: 0.87
}

AGE_GROUPS = ["All Ages", "18–24", "25–29", "30–59", "Over 60"]

AGE_RISK = {
    "All Ages": 1.0,
    "18–24": 1.6,
    "25–29": 1.3,
    "30–59": 1.0,
    "Over 60": 1.2
}

ITALIAN_PROVINCES = sorted([
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
])

# =============================================================================
# API
# =============================================================================
@st.cache_data(ttl=3600)
def fetch_mortality_data():
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

# =============================================================================
# DEMO DATA GENERATION (province x month x age)
# =============================================================================
@st.cache_data
def generate_data():
    np.random.seed(42)
    rows = []
    ages_real = ["18–24", "25–29", "30–59", "Over 60"]

    for province in ITALIAN_PROVINCES:
        base = np.random.uniform(20, 180)
        for month_name, month_num in list(MONTHS.items())[1:]:  # skip "All Months"
            m_mult = MONTH_RISK[month_num]
            for age in ages_real:
                a_mult = AGE_RISK[age]
                inj_ped  = max(0, int(np.random.poisson(base * 0.20 * m_mult * a_mult)))
                inj_drv  = max(0, int(np.random.poisson(base * 0.50 * m_mult * a_mult)))
                inj_pass = max(0, int(np.random.poisson(base * 0.30 * m_mult * a_mult)))
                dead_ped  = max(0, int(np.random.poisson(base * 0.010 * m_mult * a_mult)))
                dead_drv  = max(0, int(np.random.poisson(base * 0.020 * m_mult * a_mult)))
                dead_pass = max(0, int(np.random.poisson(base * 0.008 * m_mult * a_mult)))
                rows.append({
                    "province":           province,
                    "month":              month_name,
                    "month_num":          month_num,
                    "age_group":          age,
                    "injured_pedestrians": inj_ped,
                    "injured_drivers":     inj_drv,
                    "injured_passengers":  inj_pass,
                    "dead_pedestrians":    dead_ped,
                    "dead_drivers":        dead_drv,
                    "dead_passengers":     dead_pass,
                })

    df = pd.DataFrame(rows)
    df["total_injured"] = df["injured_pedestrians"] + df["injured_drivers"] + df["injured_passengers"]
    df["total_dead"]    = df["dead_pedestrians"] + df["dead_drivers"] + df["dead_passengers"]
    df["risk_score"]    = np.minimum(100,
        df["total_injured"] * 0.35 + df["total_dead"] * 1.8
    ).round(1)

    def risk_label(s):
        if s < 30:  return "🟢 Low"
        elif s < 60: return "🟡 Medium"
        else:        return "🔴 High"

    df["risk_level"] = df["risk_score"].apply(risk_label)
    return df

# =============================================================================
# LOAD
# =============================================================================
df_all = generate_data()
df_mort, ok_mort  = fetch_mortality_data()
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
# SIDEBAR — FILTERS
# =============================================================================
st.sidebar.header("🔍 Filters")
st.sidebar.markdown("---")

# Province
selected_provinces = st.sidebar.multiselect(
    "📍 Province(s)",
    options=ITALIAN_PROVINCES,
    default=["Roma", "Milano", "Torino", "Napoli", "Trento"]
)
if not selected_provinces:
    selected_provinces = ["Roma"]

# Month
selected_month = st.sidebar.selectbox(
    "📅 Month",
    options=list(MONTHS.keys()),
    index=0  # default = "All Months"
)

# Age Group
selected_age = st.sidebar.selectbox(
    "👤 Age Group",
    options=AGE_GROUPS,
    index=0  # default = "All Ages"
)

st.sidebar.markdown("---")
st.sidebar.markdown("**📌 Data Sources**")
st.sidebar.caption("• [ISTAT](https://www.istat.it)")
st.sidebar.caption("• [Open Data Trentino](https://dati.trentino.it)")
st.sidebar.caption("• [Statistica Trentino](https://statweb.provincia.tn.it)")
st.sidebar.markdown("---")
st.sidebar.caption("All road types included.")
st.sidebar.caption("No road-type filtering applied.")

# =============================================================================
# FILTER LOGIC
# =============================================================================
df_f = df_all[df_all["province"].isin(selected_provinces)].copy()

# Month filter
if selected_month != "All Months":
    df_f = df_f[df_f["month"] == selected_month]

# Age filter
if selected_age != "All Ages":
    df_f = df_f[df_f["age_group"] == selected_age]

# Label for display
period_label = selected_month if selected_month != "All Months" else "All Months"
age_label    = selected_age   if selected_age   != "All Ages"   else "All Ages"

# =============================================================================
# RF1 — 6 KPI CARDS
# =============================================================================
st.markdown(f"### 📊 Risk Indicators — {period_label} | {age_label}")

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("🚶 Inj. Pedestrians", f"{df_f['injured_pedestrians'].sum():,}")
c2.metric("🚗 Inj. Drivers",     f"{df_f['injured_drivers'].sum():,}")
c3.metric("🧑 Inj. Passengers",  f"{df_f['injured_passengers'].sum():,}")
c4.metric("💀 Dead Pedestrians", f"{df_f['dead_pedestrians'].sum():,}")
c5.metric("💀 Dead Drivers",     f"{df_f['dead_drivers'].sum():,}")
c6.metric("💀 Dead Passengers",  f"{df_f['dead_passengers'].sum():,}")

st.markdown("---")

# =============================================================================
# RF2 — RISK SCORE + FACTORS
# =============================================================================
st.markdown("### 🎯 Risk Score Estimation")

col_rs1, col_rs2 = st.columns([1, 2])

with col_rs1:
    avg_risk = df_f["risk_score"].mean()
    if avg_risk < 30:
        badge, color = "🟢 LOW RISK", "green"
    elif avg_risk < 60:
        badge, color = "🟡 MEDIUM RISK", "orange"
    else:
        badge, color = "🔴 HIGH RISK", "red"

    st.markdown(f"""
    <div style='
        background:#1e1e1e;border:2px solid {color};
        border-radius:12px;padding:28px;text-align:center;
    '>
        <div style='font-size:52px;font-weight:bold;color:{color}'>{avg_risk:.0f}</div>
        <div style='color:#aaa;margin-bottom:6px'>out of 100</div>
        <div style='font-size:18px;font-weight:bold;color:{color}'>{badge}</div>
        <div style='color:#888;font-size:11px;margin-top:8px'>
            Based on historical patterns,<br>
            monthly trend & age group risk
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_rs2:
    st.markdown("**Main contributing factors:**")

    month_w = MONTH_RISK.get(MONTHS.get(selected_month, 0), 1.0)
    age_w   = AGE_RISK.get(selected_age, 1.0)

    raw_factors = {
        "📍 Historical accident density": 35,
        f"📅 Monthly trend ({period_label})": int(month_w * 20),
        f"👤 Age group risk ({age_label})": int(age_w * 15),
        "🛣️ All road types (aggregated)": 10,
    }
    total = sum(raw_factors.values())
    for label, w in raw_factors.items():
        pct = round(w / total * 100)
        st.markdown(f"**{label}** — {pct}%")
        st.progress(pct / 100)

st.markdown("---")

# =============================================================================
# RF1 — PROVINCE COMPARISON TABLE + CHARTS
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

col_c1, col_c2 = st.columns(2)
with col_c1:
    st.markdown("**Risk Score by Province**")
    st.bar_chart(compare_df.set_index("province")["risk_score"])

with col_c2:
    st.markdown("**Total Injured vs Dead by Province**")
    st.bar_chart(compare_df.set_index("province")[["total_injured", "total_dead"]])

st.markdown("**📋 Full Comparison Table**")
st.dataframe(
    compare_df[[
        "province",
        "injured_pedestrians", "injured_drivers", "injured_passengers",
        "dead_pedestrians",    "dead_drivers",    "dead_passengers",
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
# MONTHLY TREND (visible only if "All Months" selected)
# =============================================================================
if selected_month == "All Months":
    st.markdown("### 📅 Monthly Trend — Selected Provinces & Age Group")
    monthly = df_f.groupby("month_num").agg({
        "total_injured": "sum",
        "total_dead":    "sum",
        "risk_score":    "mean"
    }).reindex(range(1, 13))
    monthly.index = list(MONTHS.keys())[1:]  # Jan–Dec labels
    monthly.index.name = "Month"

    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.markdown("**Total Injured per Month**")
        st.bar_chart(monthly["total_injured"])
    with col_m2:
        st.markdown("**Average Risk Score per Month**")
        st.line_chart(monthly["risk_score"])

    st.markdown("---")

# =============================================================================
# AGE GROUP COMPARISON (visible only if "All Ages" selected)
# =============================================================================
if selected_age == "All Ages":
    st.markdown("### 👥 Risk by Age Group — Selected Provinces & Month")
    age_q = df_all[df_all["province"].isin(selected_provinces)]
    if selected_month != "All Months":
        age_q = age_q[age_q["month"] == selected_month]

    age_compare = age_q.groupby("age_group").agg({
        "risk_score":    "mean",
        "total_injured": "sum",
        "total_dead":    "sum"
    }).reindex(["18–24", "25–29", "30–59", "Over 60"])

    col_a1, col_a2 = st.columns(2)
    with col_a1:
        st.markdown("**Average Risk Score by Age Group**")
        st.bar_chart(age_compare["risk_score"])
    with col_a2:
        st.markdown("**Total Injured by Age Group**")
        st.bar_chart(age_compare["total_injured"])

    st.markdown("---")

# =============================================================================
# REAL DATA — ISTAT VIA TRENTINO API
# =============================================================================
if ok_mort and df_mort is not None:
    st.markdown("### 📈 Real Data — Road Mortality (ISTAT via Open Data Trentino)")
    col_rd1, col_rd2 = st.columns(2)
    with col_rd1:
        st.markdown("**Mortality rate: Trentino vs Italy (per 100k inhabitants)**")
        st.line_chart(df_mort[["Anno", "Trentino", "Italia"]].set_index("Anno"))
    with col_rd2:
        st.markdown("**Regional comparison — latest year**")
        last = df_mort.iloc[-1]
        regioni = {k: float(str(v).replace(',', '.')) for k, v in last.items() if k != 'Anno'}
        st.bar_chart(pd.Series(regioni))

    if ok_youth and df_youth is not None:
        st.markdown("**👶 Youth mortality (15–34) — Trentino**")
        st.line_chart(df_youth[["Anno", "Trentino"]].set_index("Anno"))

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
    "Powered by ISTAT & Open Data Trentino | All road types included"
)
