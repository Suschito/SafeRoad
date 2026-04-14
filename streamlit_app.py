import streamlit as st
import pandas as pd
import requests
from io import StringIO
from datetime import datetime
import time

st.set_page_config(page_title="SafeRoad – ISTAT API", page_icon="🚗", layout="wide")

# =========================================================
# ISTAT SDMX CONFIG (GENERIC, NO HARDCODED AREA NAMES)
# =========================================================

BASE_URL = "https://esploradati.istat.it/SDMXWS/rest"
DATAFLOW_ID = "41_983"  # Incidenti, morti e feriti - comuni (esempio guida) [web:72]

HEADERS = {
    "Accept": "application/vnd.sdmx.data+csv;version=1.0.0"
}

MONTH_ORDER = [
    "2024-01", "2024-02", "2024-03", "2024-04", "2024-05", "2024-06",
    "2024-07", "2024-08", "2024-09", "2024-10", "2024-11", "2024-12"
]
MONTH_LABELS = {
    "2024-01": "January",
    "2024-02": "February",
    "2024-03": "March",
    "2024-04": "April",
    "2024-05": "May",
    "2024-06": "June",
    "2024-07": "July",
    "2024-08": "August",
    "2024-09": "September",
    "2024-10": "October",
    "2024-11": "November",
    "2024-12": "December",
}

# =========================================================
# FETCH + NORMALIZE
# =========================================================

@st.cache_data(ttl=3600)
def fetch_istat_csv():
    """
    Scarica il dataflow come CSV usando SDMX REST.
    URL semplificato: tutto il dataflow, poi filtriamo noi su 2024. [web:72][web:81]
    """
    url = f"{BASE_URL}/data/{DATAFLOW_ID}?startPeriod=2024&endPeriod=2024"

    last_error = None
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=90)
            r.raise_for_status()
            text = r.text.strip()
            if not text:
                raise ValueError("Empty response from ISTAT")
            df = pd.read_csv(StringIO(text))
            return df
        except Exception as e:
            last_error = e
            time.sleep(3)

    raise last_error


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prova a mappare nomi di colonne comuni (TIME_PERIOD, OBS_VALUE, REF_AREA, AGE, ecc.).
    Tutto il resto viene lasciato com'è ma in minuscolo.
    """
    mapping = {}
    for c in df.columns:
        cu = c.strip().upper()
        if cu == "TIME_PERIOD":
            mapping[c] = "time_period"
        elif cu == "OBS_VALUE":
            mapping[c] = "value"
        elif cu == "FREQ":
            mapping[c] = "freq"
        elif "REF_AREA" in cu or "GEO" in cu or "TERRITORIO" in cu:
            mapping[c] = "geo"
        elif "COMUNE" in cu:
            mapping[c] = "municipality"
        elif "PROVINC" in cu:
            mapping[c] = "province"
        elif "AGE" in cu or "ETA" in cu:
            mapping[c] = "age"
        elif "SEX" in cu or "SESSO" in cu:
            mapping[c] = "sex"
        elif "MEASURE" in cu or "MISURA" in cu:
            mapping[c] = "measure"
        elif "RUOLO" in cu or "TIPO_UTENTE" in cu or "ROLE" in cu:
            mapping[c] = "role"
        else:
            mapping[c] = c.strip().lower()

    df = df.rename(columns=mapping)

    # TIME_PERIOD → string, solo 2024
    if "time_period" in df.columns:
        df["time_period"] = df["time_period"].astype(str)
        df = df[df["time_period"].str.startswith("2024")]

    # OBS_VALUE → numerico
    if "value" in df.columns:
        df["value"] = pd.to_numeric(df["value"], errors="coerce")

    return df


def get_unique(df: pd.DataFrame, col: str):
    if col not in df.columns:
        return []
    return sorted(df[col].dropna().astype(str).unique().tolist())


def pick_geo_column(df: pd.DataFrame):
    """
    Sceglie una colonna geografica disponibile (province/comune/ref_area...) in ordine di preferenza.
    """
    for candidate in ["municipality", "province", "geo", "ref_area"]:
        if candidate in df.columns:
            return candidate
    return None


# =========================================================
# LOAD DATA
# =========================================================

st.title("🚗 SafeRoad – ISTAT SDMX Road Accidents (API)")
st.caption("Live data from ISTAT SDMX Web Services – example dataflow 41_983 (incidents, killed, injured). [web:72][web:81]")

with st.spinner("Fetching data from ISTAT..."):
    try:
        raw_df = fetch_istat_csv()
        df = normalize_columns(raw_df)
    except Exception as e:
        st.error("Unable to load ISTAT live data.")
        st.code(str(e))
        st.info("The SDMX service can be slow or rate‑limited; try again later.")
        st.stop()

if df.empty:
    st.error("ISTAT returned no data for 2024 after filtering.")
    st.stop()

st.success("ISTAT data loaded successfully for 2024.")
st.caption(f"Rows: {len(df):,}")

geo_col = pick_geo_column(df)

# =========================================================
# SIDEBAR FILTERS (ROBUST)
# =========================================================

st.sidebar.header("Filters")

# Geographic filter (if available)
if geo_col is not None:
    areas = get_unique(df, geo_col)
    default_areas = areas[:10] if len(areas) > 10 else areas
    selected_areas = st.sidebar.multiselect(
        "Geographical area",
        options=areas,
        default=default_areas
    )
else:
    selected_areas = []

# Month filter (TIME_PERIOD)
months_in_data = get_unique(df, "time_period")
months_available = [m for m in MONTH_ORDER if m in months_in_data]
selected_month = st.sidebar.selectbox(
    "Month",
    options=["All Months"] + months_available,
    format_func=lambda x: "All Months" if x == "All Months" else MONTH_LABELS.get(x, x)
)

# Age filter (if present)
ages = get_unique(df, "age")
selected_age = st.sidebar.selectbox(
    "Age group",
    options=["All Ages"] + ages if ages else ["All Ages"]
)

# Role filter (driver / passenger / pedestrian, if present)
roles = get_unique(df, "role")
selected_role = st.sidebar.selectbox(
    "Role",
    options=["All Roles"] + roles if roles else ["All Roles"]
)

# Measure filter (killed / injured / victims, etc.)
measures = get_unique(df, "measure")
selected_measures = st.sidebar.multiselect(
    "Measures",
    options=measures,
    default=measures[:4] if len(measures) > 0 else []
)

st.sidebar.markdown("---")
st.sidebar.caption("Source: ISTAT SDMX Web Services – dataflow 41_983. [web:72][web:81]")
st.sidebar.caption("Year filter: TIME_PERIOD starts with 2024.")

# =========================================================
# APPLY FILTERS
# =========================================================

df_f = df.copy()

if geo_col is not None and selected_areas:
    df_f = df_f[df_f[geo_col].astype(str).isin(selected_areas)]

if selected_month != "All Months" and "time_period" in df_f.columns:
    df_f = df_f[df_f["time_period"].astype(str) == selected_month]

if selected_age != "All Ages" and "age" in df_f.columns:
    df_f = df_f[df_f["age"].astype(str) == selected_age]

if selected_role != "All Roles" and "role" in df_f.columns:
    df_f = df_f[df_f["role"].astype(str) == selected_role]

if selected_measures and "measure" in df_f.columns:
    df_f = df_f[df_f["measure"].astype(str).isin(selected_measures)]

if df_f.empty:
    st.warning("No rows match the selected filters.")
    st.stop()

# =========================================================
# KPIs (GENERIC, SOLO SU VALUE)
# =========================================================

st.markdown("## Summary")

total_value = df_f["value"].sum() if "value" in df_f.columns else 0
rows_count = len(df_f)
n_areas = df_f[geo_col].nunique() if geo_col is not None and geo_col in df_f.columns else 0
n_measures = df_f["measure"].nunique() if "measure" in df_f.columns else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total OBS_VALUE", f"{total_value:,.0f}")
k2.metric("Rows", f"{rows_count:,}")
k3.metric("Areas", f"{n_areas:,}")
k4.metric("Measures", f"{n_measures:,}")

# =========================================================
# MEASURE TOTALS
# =========================================================

if "measure" in df_f.columns and "value" in df_f.columns:
    st.markdown("## Totals by measure")
    measure_totals = (
        df_f.groupby("measure")["value"]
        .sum()
        .sort_values(ascending=False)
    )
    st.bar_chart(measure_totals)

# =========================================================
# MONTHLY TREND
# =========================================================

if "time_period" in df_f.columns and "value" in df_f.columns:
    st.markdown("## Monthly trend (sum of OBS_VALUE)")
    trend = (
        df_f.groupby("time_period")["value"]
        .sum()
        .reindex(months_available)
    )
    trend.index = [MONTH_LABELS.get(m, m) for m in trend.index]
    st.line_chart(trend)

# =========================================================
# AGE COMPARISON
# =========================================================

if "age" in df_f.columns and "value" in df_f.columns:
    st.markdown("## Age group comparison")
    age_comp = (
        df_f.groupby("age")["value"]
        .sum()
        .sort_values(ascending=False)
    )
    st.bar_chart(age_comp)

# =========================================================
# ROLE COMPARISON
# =========================================================

if "role" in df_f.columns and "value" in df_f.columns:
    st.markdown("## Role comparison")
    role_comp = (
        df_f.groupby("role")["value"]
        .sum()
        .sort_values(ascending=False)
    )
    st.bar_chart(role_comp)

# =========================================================
# AREA COMPARISON
# =========================================================

if geo_col is not None and geo_col in df_f.columns and "value" in df_f.columns:
    st.markdown("## Geographical comparison")
    area_comp = (
        df_f.groupby(geo_col)["value"]
        .sum()
        .sort_values(ascending=False)
        .head(30)
    )
    st.bar_chart(area_comp)

# =========================================================
# DATA TABLE
# =========================================================

st.markdown("## Filtered data (first 200 rows)")
st.dataframe(df_f.head(200), use_container_width=True)

# =========================================================
# DEBUG
# =========================================================

with st.expander("Debug: raw ISTAT columns + sample"):
    st.write("Columns:", list(df.columns))
    st.dataframe(df.head(20), use_container_width=True)

# =========================================================
# DOWNLOAD
# =========================================================

csv = df_f.to_csv(index=False).encode("utf-8")
st.download_button(
    "Download filtered CSV",
    data=csv,
    file_name="istat_road_accidents_41_983_2024_filtered.csv",
    mime="text/csv"
)