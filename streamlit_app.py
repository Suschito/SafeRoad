import streamlit as st
import pandas as pd
import requests
from io import StringIO
from datetime import datetime
import time

st.set_page_config(page_title="SafeRoad – ISTAT API", page_icon="🚗", layout="wide")

# =========================================================
# ISTAT SDMX CONFIG
# =========================================================
# Official SDMX endpoint (IstatData SEP) [web:81]
BASE_URL = "https://esploradati.istat.it/SDMXWS/rest"

# We use the example dataflow for road accidents, killed and injured - municipalities [web:72]
DATAFLOW_ID = "41_983"  # Dataflow: Incidenti, morti e feriti - comuni

# Request CSV output as recommended in the API guide [web:72]
HEADERS = {
    "Accept": "application/vnd.sdmx.data+csv;version=1.0.0"
}

# Month helpers for nicer labels
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
# DATA FETCHING
# =========================================================
@st.cache_data(ttl=3600)
def fetch_istat_road_accidents():
    """
    Fetches entire 41_983 dataflow in CSV via SDMX REST.
    URL pattern exactly as in the official guide. [web:72]
    """
    url = f"{BASE_URL}/data/{DATAFLOW_ID}?startPeriod=2024&endPeriod=2024"

    last_error = None
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=90)
            r.raise_for_status()
            text = r.text.strip()
            if not text:
                raise ValueError("Empty response from ISTAT.")
            df = pd.read_csv(StringIO(text))
            return df
        except Exception as e:
            last_error = e
            time.sleep(3)

    raise last_error


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardise column names to something easier to use.
    Actual column names depend on the SDMX structure; we map common ones.
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
        elif "REF_AREA" in cu or "GEO" in cu or "TERR" in cu:
            mapping[c] = "area"
        elif "AGE" in cu or "ETA" in cu:
            mapping[c] = "age"
        elif "SEX" in cu or "SESSO" in cu:
            mapping[c] = "sex"
        elif "MEASURE" in cu or "MISURA" in cu:
            mapping[c] = "measure"
        elif "RESULT" in cu:
            mapping[c] = "result"
        elif "DATA_TYPE" in cu:
            mapping[c] = "data_type"
        else:
            mapping[c] = c.strip().lower()

    df = df.rename(columns=mapping)

    # coerce time to str and keep 2024 only
    if "time_period" in df.columns:
        df["time_period"] = df["time_period"].astype(str)
        df = df[df["time_period"].str.startswith("2024")]

    # numeric values
    if "value" in df.columns:
        df["value"] = pd.to_numeric(df["value"], errors="coerce")

    return df


def get_sorted_unique(df: pd.DataFrame, col: str):
    if col not in df.columns:
        return []
    return sorted(df[col].dropna().astype(str).unique().tolist())


# =========================================================
# LOAD DATA
# =========================================================
st.title("🚗 SafeRoad – Road Accident Risk Dashboard (ISTAT SDMX API)")
st.caption("Live data from ISTAT SDMX Web Services (dataflow 41_983). [web:72][web:81]")

with st.spinner("Fetching road accident data from ISTAT..."):
    try:
        raw_df = fetch_istat_road_accidents()
        df = normalize_columns(raw_df)
    except Exception as e:
        st.error("Unable to load ISTAT data.")
        st.code(str(e))
        st.info("The SDMX service has rate limits and can be slow. Please try again later. [web:81]")
        st.stop()

if df.empty:
    st.error("ISTAT returned no data for 2024.")
    st.stop()

st.success("ISTAT data loaded successfully for 2024.")

# =========================================================
# SIDEBAR FILTERS
# =========================================================
st.sidebar.header("Filters")

# Area / municipality or province, depending on how REF_AREA is defined
if "area" in df.columns:
    all_areas = get_sorted_unique(df, "area")
    default_areas = all_areas[:10] if len(all_areas) > 10 else all_areas
    selected_areas = st.sidebar.multiselect(
        "Area (municipality/province)",
        options=all_areas,
        default=default_areas
    )
else:
    selected_areas = []

# Month filter (uses TIME_PERIOD dimension)
months_available = [m for m in MONTH_ORDER if m in get_sorted_unique(df, "time_period")]
selected_month = st.sidebar.selectbox(
    "Month",
    options=["All Months"] + months_available,
    format_func=lambda x: MONTH_LABELS.get(x, x)
)

# Age filter (if available)
ages_available = get_sorted_unique(df, "age")
selected_age = st.sidebar.selectbox(
    "Age group",
    options=["All Ages"] + ages_available if ages_available else ["All Ages"]
)

# Measure filter (if available)
measures_available = get_sorted_unique(df, "measure")
selected_measures = st.sidebar.multiselect(
    "Measures",
    options=measures_available,
    default=measures_available[:4] if len(measures_available) > 0 else []
)

st.sidebar.markdown("---")
st.sidebar.caption("Source: ISTAT SDMX Web Services – dataflow 41_983. [web:72][web:81]")
st.sidebar.caption("Year: 2024 (TIME_PERIOD starting with 2024).")

# =========================================================
# APPLY FILTERS
# =========================================================
df_f = df.copy()

if selected_areas and "area" in df_f.columns:
    df_f = df_f[df_f["area"].astype(str).isin(selected_areas)]

if selected_month != "All Months" and "time_period" in df_f.columns:
    df_f = df_f[df_f["time_period"].astype(str) == selected_month]

if selected_age != "All Ages" and "age" in df_f.columns:
    df_f = df_f[df_f["age"].astype(str) == selected_age]

if selected_measures and "measure" in df_f.columns:
    df_f = df_f[df_f["measure"].astype(str).isin(selected_measures)]

if df_f.empty:
    st.warning("No rows match the selected filters.")
    st.stop()

# =========================================================
# KPI SUMMARY
# =========================================================
st.markdown("## Summary")

total_value = df_f["value"].sum() if "value" in df_f.columns else 0
obs_count = len(df_f)
n_areas = df_f["area"].nunique() if "area" in df_f.columns else 0
n_measures = df_f["measure"].nunique() if "measure" in df_f.columns else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total value (sum of OBS_VALUE)", f"{total_value:,.0f}")
k2.metric("Observations", f"{obs_count:,}")
k3.metric("Areas", f"{n_areas:,}")
k4.metric("Measures", f"{n_measures:,}")

# =========================================================
# MEASURE TOTALS
# =========================================================
if "measure" in df_f.columns and "value" in df_f.columns:
    st.markdown("## Measure totals (all filters)")
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
# AREA COMPARISON
# =========================================================
if "area" in df_f.columns and "value" in df_f.columns:
    st.markdown("## Area comparison")
    area_comp = (
        df_f.groupby("area")["value"]
        .sum()
        .sort_values(ascending=False)
        .head(30)
    )
    st.bar_chart(area_comp)

# =========================================================
# DATA TABLE
# =========================================================
st.markdown("## Detailed data")
st.dataframe(df_f.head(200), use_container_width=True)

# =========================================================
# DEBUG: RAW COLUMNS
# =========================================================
with st.expander("Debug: raw ISTAT columns and sample rows"):
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