import pandas as pd
import streamlit as st

st.set_page_config(page_title="SafeRoad - Road Accident Dashboard", layout="wide")

@st.cache_data
def load_data():
    return pd.read_csv("accidents.csv")

df = load_data()

st.title("SafeRoad - Road Accident Risk Dashboard")
st.write(
    "This dashboard shows synthetic but realistic road accident data for Italian provinces in 2024. "
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

col1, col2, col3 = st.columns(3)
col1.metric("Total accidents", f"{int(filtered['accidents'].sum()):,}")
col2.metric("Total injuries", f"{int(filtered['injuries'].sum()):,}")
col3.metric("Total fatalities", f"{int(filtered['fatalities'].sum()):,}")

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

st.subheader("Detailed data")
st.dataframe(filtered.sort_values(["province", "month", "age_group", "role"]))

st.caption("Note: this dataset is synthetic and made for demo purposes only.")