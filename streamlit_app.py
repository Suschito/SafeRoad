import streamlit as st
import pandas as pd
import requests
from io import StringIO
from datetime import datetime
import time

st.set_page_config(page_title="SafeRoad – ISTAT API DEBUG", page_icon="🚗", layout="wide")

BASE_URL = "https://esploradati.istat.it/SDMXWS/rest"
DATAFLOW_ID = "41_983"  # Incidenti, morti e feriti - comuni (esempio)

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


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    mapping = {}
    for c in df.columns:
        cu = c.strip().upper()
        if cu == "TIME_PERIOD":
            mapping[c] = "time_period"
        elif cu == "OBS_VALUE":
            mapping[c] = "value"
        else:
            mapping[c] = c.strip()
    df = df.rename(columns=mapping)

    if "time_period" in df.columns:
        df["time_period"] = df["time_period"].astype(str)
        df = df[df["time_period"].str.startswith("2024")]

    if "value" in df.columns:
        df["value"] = pd.to_numeric(df["value"], errors="coerce")

    return df


st.title("🚗 SafeRoad – ISTAT API DEBUG")
st.caption("Step 1: just load data and inspect columns for 2024.")

with st.spinner("Fetching data from ISTAT..."):
    try:
        raw_df = fetch_istat_csv()
        df = normalize_columns(raw_df)
    except Exception as e:
        st.error("Unable to load ISTAT data.")
        st.code(str(e))
        st.stop()

if df.empty:
    st.error("No rows for 2024.")
    st.stop()

st.success("ISTAT data loaded.")
st.caption(f"Rows: {len(df):,}")

# KPI super generici
if "value" in df.columns:
    st.metric("Sum of OBS_VALUE", f"{df['value'].sum():,.0f}")
st.metric("Rows", f"{len(df):,}")

st.markdown("## Columns returned by ISTAT")
st.write(list(df.columns))

st.markdown("## Sample of data")
st.dataframe(df.head(50), use_container_width=True)

# Download raw filtered data (2024 only)
csv = df.to_csv(index=False).encode("utf-8")
st.download_button(
    "Download 2024 data (raw)",
    data=csv,
    file_name="istat_41_983_2024_raw.csv",
    mime="text/csv"
)