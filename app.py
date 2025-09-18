import streamlit as st
import pandas as pd
import openai
import json
from PIL import Image
import os
import matplotlib.pyplot as plt

# ---- App Configuration ----
st.set_page_config(page_title="SupplyKai Forecast Assistant", page_icon="🌀", layout="centered")

# ---- Custom Background Styling ----
def set_background():
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("supplykai_background_image.png");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

set_background()

# ---- Display Logo ----
if os.path.exists("supplykai_logo.png"):
    logo = Image.open("supplykai_logo.png")
    st.image(logo, width=200)

st.title("SupplyKai V.01 (Big4 Monthly Rolling Forecast Assistant)")
st.caption("Upload your forecast file and ask natural questions about forecasted demand.")

# ---- Load OpenAI API Key ----
openai.api_key = st.secrets["OPENAI_API_KEY"]

# ---- File Upload ----
uploaded_file = st.file_uploader("📁 Upload your Big4RollingForecast.xlsx", type=["xlsx"])
if uploaded_file is None:
    st.warning("Please upload your forecast Excel file to continue.")
    st.stop()

# ---- Load Excel File ----
try:
    df = pd.read_excel(uploaded_file)
except Exception as e:
    st.error(f"Failed to read the Excel file: {e}")
    st.stop()

# ---- Month Column Map ----
month_column_map = {
    "April 2026": "SU26 M1",
    "May 2026": "SU26 M2",
    "June 2026": "SU26 M3",
    "July 2026": "FAL26 M1",
    "August 2026": "FAL26 M2",
    "September 2026": "FAL26 M3"
}

# ---- Core Functions ----
def forecast_lookup(collection: str, month: str, year: int) -> str:
    full_month = f"{month} {year}"
    if full_month not in month_column_map:
        return f"⚠️ Sorry, no forecast data available for {full_month}."
    target_column = month_column_map[full_month]
    if target_column not in df.columns:
        return f"⚠️ The column '{target_column}' is missing from the file."
    filtered = df[df["Style Collection"].str.strip().str.lower() == collection.lower()]
    if filtered.empty:
        return f"⚠️ No data for collection '{collection}'."
    total = filtered[target_column].sum()
    return f"📊 Forecast for **{collection}** in **{full_month}** is: **{int(total):,} units**."

def total_forecast_for_collection(collection: str) -> str:
    forecast_cols = list(month_column_map.values())
    missing = [c for c in forecast_cols if c not in df.columns]
    if missing:
        return f"⚠️ Missing columns: {', '.join(missing)}"
    filtered = df[df["Style Collection"].str.strip().str.lower() == collection.lower()]
    if filtered.empty:
        return f"⚠️ No data for collection '{collection}'."
    total = filtered[forecast_cols].sum().sum()
    return f"📊 Total forecast for **{collection}** is: **{int(total):,} units**."

def top_collection_for_month(month: str, year: int) -> str:
    full_month = f"{month} {year}"
    if full_month not in month_column_map:
        return f"⚠️ No data for {full_month}."
    col = month_column_map[full_month]
    if col not in df.columns:
        return f"⚠️ Missing column '{col}'."
    grouped = df.groupby("Style Collection")[col].sum().reset_index()
    if grouped.empty:
        return "⚠️ No collections found."
    top = grouped.sort_values(by=col, ascending=False).iloc[0]
    return f"🏆 Highest forecast in **{full_month}**: **{top['Style Collection']}** with **{int(top[col]):,} units**."

def top_3_styles(collection: str, month: str, year: int) -> str:
    full_month = f"{month} {year}"
    if full_month not in month_column_map:
        return f"⚠️ No data for {full_month}."
    col = month_column_map[full_month]
    filtered = df[df["Style Collection"].str.strip().str.lower() == collection.lower()]
    if filtered.empty:
        return f"⚠️ No data for collection '{collection}'."
    if col not in filtered.columns:
        return f"⚠️ Missing column '{col}'."
    top = filtered.sort_values(by=col, ascending=False).head(3)
    if top.empty:
        return f"⚠️ No styles found for {collection}."
    rows = [f"**{row['Style Number']}**: {int(row[col]):,} units" for _, row in top.iterrows()]
    return f"🏅 Top 3 styles in **{collection}** for **{full_month}**:\n\n" + "\n\n".join(rows)

def month_to_month_change(collection: str) -> str:
    forecast_cols = list(month_column_map.values())
    filtered = df[df["Style Collection"].str.strip().str.lower() == collection.lower()]
    if filtered.empty:
        return f"⚠️ No data for collection '{collection}'."
    totals = filtered[forecast_cols].sum()
    diffs = totals.diff().fillna(0)
    report = [f"📈 **{month}**: Δ {int(diffs[col]):,} units"
              for month, col in month_column_map.items()]
    return f"📊 Month-over-month change for **{collection}**:\n\n" + "\n".join(report)

def chart_forecast(collection: str):
    forecast_cols = list(month_column_map.values())
    filtered = df[df["Style Collection"].str.strip().str.lower() == collection.lower()]
    if filtered.empty:
        st.warning(f"No data for collection '{collection}' to show chart.")
        return
    totals = filtered[forecast_cols].sum()
    plt.figure(figsize=(8, 4))
    plt.plot(list(month_column_map.keys()), totals.values, marker='o', color='#1f77b4')
    plt.title(f"📈 Forecast Trend for {collection}")
    plt.xlabel("Month")
    plt.ylabel("Units")
    plt.grid(True)
    st.pyplot(plt)

# ---- Define Functions for OpenAI ----
functions = [
    {
        "name": "forecast_lookup",
        "description": "Get forecasted demand for a specific style collection and month",
        "parameters": {
            "type": "object",
            "properties": {
                "collection": {"type": "string"},
                "month": {"type": "string"},
                "year": {"type": "integer"}
            },
            "required": ["collection", "month", "year"]
        }
    },
    {
        "name": "total_forecast_for_collection",
        "description": "Get total forecast for a collection",
        "parameters": {
            "type": "object",
            "properties": {
                "collection": {"type": "string"}
            },
            "required": ["collection"]
        }
    },
    {
        "name": "top_collection_for_month",
        "description": "Get collection with highest forecast in a month",
        "parameters": {
            "type": "object",
            "properties": {
                "month": {"type": "string"},
                "year": {"type": "integer"}
            },
            "required": ["month", "year"]
        }
    },
    {
        "name": "top_3_styles",
        "description": "Get top 3 styles in a collection for a month",
        "parameters": {
            "type": "object",
            "properties": {
                "collection": {"type": "string"},
                "month": {"type": "string"},
                "year": {"type": "integer"}
            },
            "required": ["collection", "month", "year"]
        }
    },
    {
        "name": "month_to_month_change",
        "description": "Get month-to-month change for a collection",
        "parameters": {
            "type": "object",
            "properties": {
                "collection": {"type": "string"}
            },
            "required": ["collection"]
        }
    },
    {
        "name": "chart_forecast",
        "description": "Show line chart for a collection's forecast over months",
        "parameters": {
            "type": "object",
            "properties": {
                "collection": {"type": "string"}
            },
            "required": ["collection"]
        }
    }
]

# ---- Handle User Questions ----
user_question = st.text_input("💬 Ask your forecast question:")

if user_question:
    with st.spinner("Thinking..."):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": user_question}],
                functions=functions,
                function_call="auto"
            )
            message = response.choices[0].message
            if message.get("function_call"):
                name = message["function_call"]["name"]
                args = json.loads(message["function_call"]["arguments"])
                if name == "forecast_lookup":
                    answer = forecast_lookup(**args)
                    st.success(answer)
                elif name == "total_forecast_for_collection":
                    answer = total_forecast_for_collection(**args)
                    st.success(answer)
                elif name == "top_collection_for_month":
                    answer = top_collection_for_month(**args)
                    st.success(answer)
                elif name == "top_3_styles":
                    answer = top_3_styles(**args)
                    st.success(answer)
                elif name == "month_to_month_change":
                    answer = month_to_month_change(**args)
                    st.success(answer)
                elif name == "chart_forecast":
                    chart_forecast(**args)
            else:
                st.success(message["content"])
        except Exception as e:
            st.error(f"An error occurred:\n\n{e}")






