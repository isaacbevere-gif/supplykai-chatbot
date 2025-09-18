import streamlit as st
import pandas as pd
import openai
import json
from PIL import Image
import os
import matplotlib.pyplot as plt
import base64

# ---- Page Config ----
st.set_page_config(page_title="SupplyKai Assistant v.01", page_icon=None, layout="centered")

# ---- Set Background ----
def set_background():
    file_path = "supplykai_background_image.jpeg"
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        st.markdown(
            f"""
            <style>
            .stApp {{
                background-image: url("data:image/png;base64,{encoded}");
                background-size: cover;
                background-repeat: no-repeat;
                background-attachment: fixed;
                background-position: center;
            }}
            </style>
            """,
            unsafe_allow_html=True
        )

set_background()

# ---- Logo ----
if os.path.exists("supplykai_logo.png"):
    logo = Image.open("supplykai_logo.png")
    st.image(logo, width=200)

st.title("SupplyKai Assistant v.01 (Big4 Monthly Rolling Forecast)")
st.caption("Upload your forecast file and ask questions.")

# ---- API Key ----
openai.api_key = st.secrets["OPENAI_API_KEY"]

# ---- File Upload ----
uploaded_file = st.file_uploader("📁 Upload your Big4RollingForecast.xlsx", type=["xlsx"])
if uploaded_file is None:
    st.warning("Upload a forecast file to begin.")
    st.stop()

try:
    df = pd.read_excel(uploaded_file)
except Exception as e:
    st.error(f"Error reading file: {e}")
    st.stop()

# ---- Month Mapping ----
month_column_map = {
    "April 2026": "SU26 M1",
    "May 2026": "SU26 M2",
    "June 2026": "SU26 M3",
    "July 2026": "FAL26 M1",
    "August 2026": "FAL26 M2",
    "September 2026": "FAL26 M3"
}

# ---- Forecast Functions ----

def forecast_lookup(collection, month, year):
    col = month_column_map.get(f"{month} {year}")
    filtered = df[df["Style Collection"].str.lower() == collection.lower()]
    if not col or col not in df.columns or filtered.empty:
        return f"⚠️ No data for {collection} in {month} {year}."
    total = filtered[col].sum()
    return f"📊 Forecast for **{collection}** in **{month} {year}**: **{int(round(total)):,} units**."

def total_forecast_for_collection(collection):
    cols = list(month_column_map.values())
    filtered = df[df["Style Collection"].str.lower() == collection.lower()]
    if filtered.empty:
        return f"⚠️ No data for {collection}."
    total = filtered[cols].sum().sum()
    return f"📈 Total forecast for **{collection}**: **{int(round(total)):,} units**."

def top_collection_for_month(month, year):
    col = month_column_map.get(f"{month} {year}")
    if not col or col not in df.columns:
        return f"⚠️ No data for {month} {year}."
    top = df.groupby("Style Collection")[col].sum().sort_values(ascending=False).reset_index().iloc[0]
    return f"🏆 Top collection for **{month} {year}**: **{top['Style Collection']}** with **{int(round(top[col])):,} units**."

def top_3_styles(collection, month, year):
    full_month = f"{month} {year}"
    col = month_column_map.get(full_month)
    filtered = df[df["Style Collection"].str.lower() == collection.lower()]

    if not col or col not in df.columns or filtered.empty:
        st.warning(f"⚠️ No data for {collection} in {full_month}.")
        return

    top = filtered.sort_values(by=col, ascending=False).head(3)
    top["Label"] = top["Style Number"].astype(str) + " – " + top["Description"]
    values = top[col].round().astype(int).values
    labels = top["Label"].values

    st.subheader(f"🏅 Top 3 styles in {collection} for {full_month}")
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(labels, values, color="#1f77b4")
    ax.set_ylim(0, max(values) * 1.2)
    ax.set_title(f"Top 3 Styles – {collection} – {full_month}")
    ax.set_ylabel("Units")

    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + max(values) * 0.05, f"{value:,}", ha="center", fontsize=10, fontweight="bold")

    plt.xticks(rotation=0)
    plt.tight_layout()
    st.pyplot(fig)

    st.dataframe(top[["Style Number", "Description", col]])
    csv = top[["Style Number", "Description", col]].to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download CSV", csv, file_name=f"top_styles_{collection}_{month}_{year}.csv")

def monthly_variance_for_collection(collection):
    cols = list(month_column_map.values())
    filtered = df[df["Style Collection"].str.lower() == collection.lower()]
    if filtered.empty:
        return f"⚠️ No data for {collection}."
    totals = filtered[cols].sum()
    pct_change = totals.pct_change().fillna(0) * 100
    return f"📈 Month-over-month % change for **{collection}**:\n\n" + "\n".join(
        [f"**{month}**: {pct_change[col]:+.1f}%" for month, col in month_column_map.items()]
    )

def month_to_month_change(collection):
    cols = list(month_column_map.values())
    filtered = df[df["Style Collection"].str.lower() == collection.lower()]
    if filtered.empty:
        return f"⚠️ No data for {collection}."
    totals = filtered[cols].sum()
    diffs = totals.diff().fillna(0)
    return f"📊 Month-over-month unit change for **{collection}**:\n\n" + "\n".join(
        [f"**{month}**: Δ {int(round(diffs[col])):,} units" for month, col in month_column_map.items()]
    )

def color_performance_for_style(style_number):
    cols = list(month_column_map.values())
    filtered = df[df["Style Number"].astype(str).str.lower() == style_number.lower()]
    if filtered.empty:
        st.warning(f"No data for style {style_number}.")
        return

    grouped = filtered.groupby("Color")[cols].sum()
    grouped["Total Units"] = grouped.sum(axis=1)
    grouped = grouped.sort_values("Total Units", ascending=False)

    st.subheader(f"🎨 Color Performance for Style {style_number}")

    # Bar chart with labels
    labels = grouped.index.tolist()
    values = grouped["Total Units"].round().astype(int).tolist()

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(labels, values, color="#6baed6")
    ax.set_title(f"Units by Color – Style {style_number}")
    ax.set_ylabel("Units")
    ax.set_ylim(0, max(values) * 1.2)

    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + max(values) * 0.05, f"{value:,}", ha="center", fontsize=9)

    plt.xticks(rotation=0)
    plt.tight_layout()
    st.pyplot(fig)

    st.dataframe(grouped)

    csv = grouped.reset_index().to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download Color Breakdown CSV", data=csv, file_name=f"color_performance_{style_number}.csv")

# ---- OpenAI Functions ----
functions = [
    {
        "name": "forecast_lookup",
        "description": "Get forecast for a collection and month",
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
            "properties": {"collection": {"type": "string"}},
            "required": ["collection"]
        }
    },
    {
        "name": "top_collection_for_month",
        "description": "Find top collection for a given month",
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
        "description": "Top 3 styles in a collection for a month",
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
        "name": "monthly_variance_for_collection",
        "description": "Get MoM % variance for a collection",
        "parameters": {
            "type": "object",
            "properties": {"collection": {"type": "string"}},
            "required": ["collection"]
        }
    },
    {
        "name": "month_to_month_change",
        "description": "Get MoM unit change for a collection",
        "parameters": {
            "type": "object",
            "properties": {"collection": {"type": "string"}},
            "required": ["collection"]
        }
    },
    {
        "name": "color_performance_for_style",
        "description": "Chart of units by color for a style",
        "parameters": {
            "type": "object",
            "properties": {"style_number": {"type": "string"}},
            "required": ["style_number"]
        }
    }
]

# ---- User Input + OpenAI Call ----
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
            msg = response.choices[0].message
            if msg.get("function_call"):
                name = msg["function_call"]["name"]
                args = json.loads(msg["function_call"]["arguments"])
                match name:
                    case "forecast_lookup":
                        st.success(forecast_lookup(**args))
                    case "total_forecast_for_collection":
                        st.success(total_forecast_for_collection(**args))
                    case "top_collection_for_month":
                        st.success(top_collection_for_month(**args))
                    case "top_3_styles":
                        top_3_styles(**args)
                    case "monthly_variance_for_collection":
                        st.success(monthly_variance_for_collection(**args))
                    case "month_to_month_change":
                        st.success(month_to_month_change(**args))
                    case "color_performance_for_style":
                        color_performance_for_style(**args)
            else:
                st.success(msg["content"])
        except Exception as e:
            st.error(f"❌ Error: {e}")













