import streamlit as st
import pandas as pd
import requests
from io import StringIO
from datetime import datetime
import time

st.set_page_config(page_title="SafeRoad – ISTAT API", page_icon="🚗", layout="wide")

BASE_URL = "https://esploradati.istat.it/SDMXWS/rest"
DATAFLOW_ID = "41_983"  # Incidenti, morti e feriti - comuni

HEADERS = {
    "Accept": "application/vnd.sdmx.data+csv;version=1.0.0"
}

@st.cache_data(ttl=3600)
def fetch_istat_csv():
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

def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    # normalizza nomi
    df = df.rename(columns={
        "REF_AREA": "ref_area",
        "DATA_TYPE": "data_type",
        "RESULT": "result",
        "time_period": "time_period",
        "value": "value"
    })
    # solo 2024
    df["time_period"] = df["time_period"].astype(str)
    df = df[df["time_period"].str.startswith("2024")]
    # value numerico
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df

def get_unique(df, col):
    return sorted(df[col].dropna().astype(str).unique().tolist()) if col in df.columns else []

# =========================================================
# LOAD
# =========================================================
st.title("🚗 SafeRoad – ISTAT SDMX (41_983)")
st.caption("Road accidents, killed and injured by territory, 2024 – live from ISTAT SDMX Web Services. [web:72][web:81]")

with st.spinner("Fetching data from ISTAT..."):
    try:
        raw_df = fetch_istat_csv()
        df = preprocess(raw_df)
    except Exception as e:
        st.error("Unable to load ISTAT data.")
        st.code(str(e))
        st.stop()

if df.empty:
    st.error("No rows for 2024.")
    st.stop()

st.success(f"ISTAT data loaded. Rows: {len(df):,}")

# =========================================================
# SIDEBAR FILTERS
# =========================================================
st.sidebar.header("Filters")

# territorio (ref_area è un codice; per ora usiamo solo il codice)
areas = get_unique(df, "ref_area")
default_areas = areas[:10] if len(areas) > 10 else areas
selected_areas = st.sidebar.multiselect(
    "Territory code (REF_AREA)",
    options=areas,
    default=default_areas
)

# data_type: KILLINJ (killed + injured) oppure ROADACC (incidenti)
types = get_unique(df, "data_type")
selected_types = st.sidebar.multiselect(
    "Data type",
    options=types,
    default=types
)

# result: F, M, 9 ecc.
results = get_unique(df, "result")
selected_results = st.sidebar.multiselect(
    "Result category",
    options=results,
    default=results
)

st.sidebar.markdown("---")
st.sidebar.caption("Columns available: REF_AREA (territory code), DATA_TYPE (KILLINJ / ROADACC), RESULT, time_period, value. [file:137]")

# =========================================================
# APPLY FILTERS
# =========================================================
df_f = df.copy()

if selected_areas:
    df_f = df_f[df_f["ref_area"].astype(str).isin(selected_areas)]

if selected_types:
    df_f = df_f[df_f["data_type"].astype(str).isin(selected_types)]

if selected_results:
    df_f = df_f[df_f["result"].astype(str).isin(selected_results)]

if df_f.empty:
    st.warning("No rows match the selected filters.")
    st.stop()

# =========================================================
# KPI
# =========================================================
st.markdown("## Summary")

total_value = df_f["value"].sum()
rows_count = len(df_f)
n_areas = df_f["ref_area"].nunique()
n_types = df_f["data_type"].nunique()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total value", f"{total_value:,.0f}")
c2.metric("Rows", f"{rows_count:,}")
c3.metric("Territories (REF_AREA)", f"{n_areas:,}")
c4.metric("Data types", f"{n_types:,}")

# =========================================================
# TOTAL BY DATA_TYPE
# =========================================================
st.markdown("## Totals by DATA_TYPE")
tot_by_type = (
    df_f.groupby("data_type")["value"]
    .sum()
    .sort_values(ascending=False)
)
st.bar_chart(tot_by_type)

# =========================================================
# TOTAL BY RESULT (e.g. F, M)
# =========================================================
st.markdown("## Totals by RESULT")
tot_by_res = (
    df_f.groupby("result")["value"]
    .sum()
    .sort_values(ascending=False)
)
st.bar_chart(tot_by_res)

# =========================================================
# TERRITORY COMPARISON
# =========================================================
st.markdown("## Territory comparison (REF_AREA)")
area_comp = (
    df_f.groupby("ref_area")["value"]
    .sum()
    .sort_values(ascending=False)
    .head(30)
)
st.bar_chart(area_comp)

# =========================================================
# TABLE
# =========================================================
st.markdown("## Filtered data (first 200 rows)")
st.dataframe(df_f.head(200), use_container_width=True)

# =========================================================
# DOWNLOAD
# =========================================================
csv = df_f.to_csv(index=False).encode("utf-8")
st.download_button(
    "Download filtered CSV",
    data=csv,
    file_name="istat_41_983_2024_filtered.csv",
    mime="text/csv"
)