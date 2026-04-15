import pandas as pd
import numpy as np
import streamlit as st

st.set_page_config(page_title="SafeRoad - Road Accident Dashboard", layout="wide")

@st.cache_data
def load_data():
    return pd.read_csv("accidents.csv")

def compute_risk_score(df):
    agg = df.groupby("province", as_index=False).agg(
        accidents=("accidents", "sum"),
        injuries=("injuries", "sum"),
        fatalities=("fatalities", "sum")
    )
    max_acc = max(agg["accidents"].max(), 1)
    max_inj = max(agg["injuries"].max(), 1)
    max_fat = max(agg["fatalities"].max(), 1)
    agg["risk_score"] = (
        0.5 * (agg["accidents"] / max_acc) * 100 +
        0.3 * (agg["injuries"] / max_inj) * 100 +
        0.2 * (agg["fatalities"] / max_fat) * 100
    )
    agg["risk_score"] = agg["risk_score"].round(1)
    agg["risk_level"] = pd.cut(
        agg["risk_score"],
        bins=[-np.inf, 33, 66, np.inf],
        labels=["Low", "Medium", "High"]
    )
    return agg.sort_values("risk_score", ascending=False)

df = load_data()
risk_by_province = compute_risk_score(df)

st.title("SafeRoad - Road Accident Risk Dashboard")
st.write(
    "This dashboard shows ISTAT road accident data for Italian provinces in 2024. "
    "Use the filters on the left to explore risk by month, province, age group, and role."
)

st.sidebar.title("Filters")

provinces = sorted(df["province"].unique())
age_groups = ["18-20", "20-24", "25-29", "30-44", "45-54", "55-59", "60-64", "65+"]
roles = ["Driver", "Passenger", "Pedestrian"]
months = list(range(1, 13))

province_sel = st.sidebar.multiselect("Province", provinces, default=provinces)
month_sel = st.sidebar.multiselect("Month (1-12)", months, default=months)
age_sel = st.sidebar.multiselect("Age group", age_groups, default=age_groups)
role_sel = st.sidebar.multiselect("Role", roles, default=roles)

mask = (
    df["province"].isin(province_sel)
    & df["month"].isin(month_sel)
    & df["age_group"].isin(age_sel)
    & df["role"].isin(role_sel)
)
filtered = df[mask].copy()

prov_mask = risk_by_province["province"].isin(province_sel)
risk_filtered = risk_by_province[prov_mask].copy()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total accidents", f"{int(filtered['accidents'].sum()):,}")
col2.metric("Total injuries", f"{int(filtered['injuries'].sum()):,}")
col3.metric("Total fatalities", f"{int(filtered['fatalities'].sum()):,}")
col4.metric("Highest risk score", f"{risk_filtered['risk_score'].max():.1f}" if not risk_filtered.empty else "0.0")

st.markdown("---")

left, right = st.columns(2)

with left:
    st.subheader("Accidents by month")
    by_month = filtered.groupby("month", as_index=False)[["accidents", "injuries", "fatalities"]].sum().sort_values("month")
    if by_month.empty:
        st.info("No data for the selected filters.")
    else:
        st.line_chart(by_month.set_index("month"))

with right:
    st.subheader("Accidents by province")
    by_prov = filtered.groupby("province", as_index=False)[["accidents", "injuries", "fatalities"]].sum().sort_values("accidents", ascending=False)
    if by_prov.empty:
        st.info("No data for the selected filters.")
    else:
        st.bar_chart(by_prov.set_index("province")[["accidents", "injuries", "fatalities"]])

st.markdown("---")

st.subheader("Risk score by province")
if risk_filtered.empty:
    st.info("No data for the selected filters.")
else:
    risk_view = risk_filtered[["province", "risk_score", "risk_level", "accidents", "injuries", "fatalities"]].copy()
    st.dataframe(risk_view, use_container_width=True)
    st.bar_chart(risk_view.set_index("province")["risk_score"])

st.markdown("---")

st.subheader("Accidents by age group")
by_age = filtered.groupby("age_group", as_index=False)[["accidents", "injuries", "fatalities"]].sum()
age_order = {"18-20": 1, "20-24": 2, "25-29": 3, "30-44": 4, "45-54": 5, "55-59": 6, "60-64": 7, "65+": 8}
by_age["order"] = by_age["age_group"].map(age_order)
by_age = by_age.sort_values("order").drop(columns="order")
if by_age.empty:
    st.info("No data for the selected filters.")
else:
    st.bar_chart(by_age.set_index("age_group"))

st.markdown("---")