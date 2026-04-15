import pandas as pd
import streamlit as st

# --------------------------------------------------
# 1. Load data
# --------------------------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv("accidents_synthetic.csv")
    return df

df = load_data()

st.set_page_config(
    page_title="SafeRoad – Road Accident Dashboard",
    layout="wide"
)

# --------------------------------------------------
# 2. Sidebar filters
# --------------------------------------------------
st.sidebar.title("Filters")

years = sorted(df["year"].unique())
provinces = sorted(df["province"].unique())
age_groups = df["age_group"].unique()
roles = df["role"].unique()
months = list(range(1, 13))

year_sel = st.sidebar.multiselect(
    "Year",
    years,
    default=years
)

province_sel = st.sidebar.multiselect(
    "Province",
    provinces,
    default=provinces
)

month_sel = st.sidebar.multiselect(
    "Month (1–12)",
    months,
    default=months
)

age_sel = st.sidebar.multiselect(
    "Age group",
    age_groups,
    default=list(age_groups)
)

role_sel = st.sidebar.multiselect(
    "Role",
    roles,
    default=list(roles)
)

# Apply filters
mask = (
    df["year"].isin(year_sel)
    & df["province"].isin(province_sel)
    & df["month"].isin(month_sel)
    & df["age_group"].isin(age_sel)
    & df["role"].isin(role_sel)
)

filtered = df[mask].copy()

# --------------------------------------------------
# 3. Header
# --------------------------------------------------
st.title("SafeRoad – Road Accident Risk Dashboard")
st.write(
    "This dashboard shows synthetic but realistic road accident data for Italian provinces. "
    "Use the filters on the left to explore risk by year, month, province, age group, and role."
)

# --------------------------------------------------
# 4. KPI cards
# --------------------------------------------------
total_acc = int(filtered["accidents"].sum())
total_inj = int(filtered["injuries"].sum())
total_fat = int(filtered["fatalities"].sum())

col1, col2, col3 = st.columns(3)

col1.metric("Total accidents", f"{total_acc:,}")
col2.metric("Total injuries", f"{total_inj:,}")
col3.metric("Total fatalities", f"{total_fat:,}")

st.markdown("---")

# --------------------------------------------------
# 5. Charts – by month and by province
# --------------------------------------------------
# Aggregation by month
by_month = (
    filtered.groupby(["year", "month"], as_index=False)[["accidents", "injuries", "fatalities"]]
    .sum()
    .sort_values(["year", "month"])
)

# Aggregation by province
by_prov = (
    filtered.groupby("province", as_index=False)[["accidents", "injuries", "fatalities"]]
    .sum()
    .sort_values("accidents", ascending=False)
)

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Accidents by month")
    if by_month.empty:
        st.info("No data for the selected filters.")
    else:
        # nice label year-month
        by_month["year_month"] = by_month["year"].astype(str) + "-" + by_month["month"].astype(str).str.zfill(2)
        st.line_chart(
            by_month.set_index("year_month")[["accidents", "injuries", "fatalities"]]
        )

with col_right:
    st.subheader("Accidents by province")
    if by_prov.empty:
        st.info("No data for the selected filters.")
    else:
        st.bar_chart(
            by_prov.set_index("province")[["accidents", "injuries", "fatalities"]]
        )

st.markdown("---")

# --------------------------------------------------
# 6. Detailed table
# --------------------------------------------------
st.subheader("Detailed data")

st.dataframe(
    filtered.sort_values(["year", "province", "month", "age_group", "role"])
)

st.caption(
    "Note: data are fully synthetic and only used for demonstration."
)