import streamlit as st
import pandas as pd
import requests
from io import StringIO
from datetime import datetime
import time

st.set_page_config(page_title="SafeRoad – ISTAT SDMX (Morti & feriti)", page_icon="🚗", layout="wide")

# === INCOLLA QUI LA TUA QUERY DEL DATO (SENZA format) ===
ISTAT_BASE_URL = "https://esploradati.istat.it/SDMXWS/rest/data/IT1,41_270_DF_DCIS_MORTIFERITISTR1_1,1.0/A..KILLINJ........99/ALL/?detail=full&startPeriod=2024-01-01&endPeriod=2024-12-31&dimensionAtObservation=TIME_PERIOD"

HEADERS = {
    "Accept": "application/vnd.sdmx.data+csv;version=1.0.0"  # CSV SDMX come da guida [web:72]
}

@st.cache_data(ttl=3600)
def fetch_istat_csv():
    # se aggiungiamo &format=csv doppio non dà fastidio, ma l'header già basta [web:87]
    url = ISTAT_BASE_URL
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
    # Normalizza solo TIME_PERIOD e OBS_VALUE, lascia il resto com'è
    if "TIME_PERIOD" in df.columns:
        df["TIME_PERIOD"] = df["TIME_PERIOD"].astype(str)
        df = df[df["TIME_PERIOD"].str.startswith("2024")]
    if "OBS_VALUE" in df.columns:
        df["OBS_VALUE"] = pd.to_numeric(df["OBS_VALUE"], errors="coerce")
    return df

def get_unique(df, col):
    return sorted(df[col].dropna().astype(str).unique().tolist()) if col in df.columns else []

# =========================================================
# LOAD DATA
# =========================================================
st.title("🚗 SafeRoad – ISTAT SDMX (Morti e feriti, 41_270)")
st.caption("Dataflow: 41_270_DF_DCIS_MORTIFERITISTR1_1 – query KILLINJ, 2024, TIME_PERIOD. [web:72][web:81]")

with st.spinner("Fetching data from ISTAT SDMX..."):
    try:
        raw_df = fetch_istat_csv()
        df = preprocess(raw_df)
    except Exception as e:
        st.error("Unable to load ISTAT data from the new query.")
        st.code(str(e))
        st.info("If this keeps failing, we will switch to manual CSV export.")
        st.stop()

if df.empty:
    st.error("No rows returned for 2024 with this query.")
    st.stop()

st.success(f"ISTAT data loaded. Rows: {len(df):,}")

value_col = "OBS_VALUE"
time_col = "TIME_PERIOD"

# =========================================================
# SIDEBAR (SOLO FILTRI SEMPLICI)
# =========================================================
st.sidebar.header("Filters")

# Filtri su colonne principali se esistono
dimensions = [c for c in df.columns if c not in ["DATAFLOW", "OBS_VALUE", "TIME_PERIOD", "OBS_STATUS",
                                                 "NOTE_DS", "NOTE_REF_AREA", "NOTE_DATA_TYPE",
                                                 "NOTE_RESULT", "NOTE_TIME_PERIOD", "BASE_PER",
                                                 "UNIT_MEAS", "UNIT_MULT"]]

# Proviamo almeno REF_AREA, AGE, SEX, ecc. se presenti
main_dim = None
for cand in ["REF_AREA", "ETA", "AGE", "SESSO", "SEX", "TIPO_UTENTE", "RUOLO_UTENTE"]:
    if cand in df.columns:
        main_dim = cand
        break

if main_dim:
    vals = get_unique(df, main_dim)
    default_vals = vals[:10] if len(vals) > 10 else vals
    selected_vals = st.sidebar.multiselect(
        f"{main_dim} filter",
        options=vals,
        default=default_vals
    )
else:
    selected_vals = []

# filtro mese (TIME_PERIOD)
months = get_unique(df, time_col)
selected_month = st.sidebar.selectbox(
    "TIME_PERIOD",
    options=["All"] + months
)

st.sidebar.markdown("---")
st.sidebar.caption("Raw SDMX query from EsploraDati; no invented columns.")

# =========================================================
# APPLY FILTERS
# =========================================================
df_f = df.copy()

if main_dim and selected_vals:
    df_f = df_f[df_f[main_dim].astype(str).isin(selected_vals)]

if selected_month != "All":
    df_f = df_f[df_f[time_col].astype(str) == selected_month]

if df_f.empty:
    st.warning("No rows match the selected filters.")
    st.stop()

# =========================================================
# KPI GENERICI
# =========================================================
st.markdown("## Summary")

total_value = df_f[value_col].sum()
rows_count = len(df_f)

c1, c2, c3 = st.columns(3)
c1.metric("Total OBS_VALUE", f"{total_value:,.0f}")
c2.metric("Rows", f"{rows_count:,}")
if main_dim:
    c3.metric(f"Distinct {main_dim}", f"{df_f[main_dim].nunique():,}")
else:
    c3.metric("Distinct groups", "-")

# =========================================================
# TREND PER TIME_PERIOD
# =========================================================
st.markdown("## Trend by TIME_PERIOD")
trend = (
    df_f.groupby(time_col)[value_col]
    .sum()
    .sort_index()
)
st.line_chart(trend)

# =========================================================
# DISTRIBUZIONE PER DIMENSIONE PRINCIPALE
# =========================================================
if main_dim:
    st.markdown(f"## Distribution by {main_dim}")
    dist = (
        df_f.groupby(main_dim)[value_col]
        .sum()
        .sort_values(ascending=False)
        .head(30)
    )
    st.bar_chart(dist)

# =========================================================
# TABELLA
# =========================================================
st.markdown("## Sample of data (first 200 rows)")
st.dataframe(df_f.head(200), use_container_width=True)

# =========================================================
# DEBUG
# =========================================================
with st.expander("Debug: columns + first rows"):
    st.write("Columns:", list(df.columns))
    st.dataframe(df.head(20), use_container_width=True)

# =========================================================
# DOWNLOAD
# =========================================================
csv = df_f.to_csv(index=False).encode("utf-8")
st.download_button(
    "Download filtered CSV",
    data=csv,
    file_name="istat_41_270_MORTIFERITISTR1_2024_filtered.csv",
    mime="text/csv"
)