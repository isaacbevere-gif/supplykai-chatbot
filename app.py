import streamlit as st
import pandas as pd
import openai
import json
from PIL import Image
import os
import matplotlib.pyplot as plt
import io

# ---- App Configuration ----
st.set_page_config(page_title="SupplyKai Forecast Assistant", page_icon="🌀", layout="centered")

# ---- Background Image ----
def set_background():
    st.markdown(
        """
        <style>
        .stApp {
            background-image: url('supplykai_background_image.png');
            background-size: cover;
            background-repeat: no-repeat;
            background-position: center;
            background-attachment: fixed;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

set_background()

# ---- Logo ----
if os.path.exists("supplykai_logo.png"):
    logo = Image.open("supplykai_logo.png")
    st.image(logo, width=200)

st.title("📦 SupplyKai Forecast Assistant")
st.caption("Ask me anything about your rolling forecast.")

# ---- API Key ----
openai.api_key = st.secrets["OPENAI_API_KEY"]

# ---- Upload Excel ----
uploaded_file = st.file_uploader("📁 Upload your Big4RollingForecast.xlsx", type=["xlsx"])
if uploaded_file is None:
    st.warning("Upload your forecast Excel file to continue.")
    st.stop()

try:
    df = pd.read_excel(uploaded_file)
except Exception as e:
    st.error(f"Failed to load file: {e}")
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

# ---- Helper Functions ----

def forecast_lookup(collection, month, year):
    full_month = f"{month} {year}"
    col = month_column_map.get(full_month)
    if not col or col not in df.columns:
        return f"⚠️ No forecast data for {full_month}."
    filtered = df[df["Style Collection"].str.lower() == collection.lower()]
    if filtered.empty:
        return f"⚠️ No data for '{collection}'."
    total = filtered[col].sum()
    return f"📊 Forecast for **{collection}** in **{full_month}**: **{int(total):,} units**."

def total_forecast_for_collection(collection):
    cols = list(month_column_map.values())
    filtered = df[df["Style Collection"].str.lower() == collection.lower()]
    if filtered.empty:
        return f"⚠️ No data for '{collection}'."
    total = filtered[cols].sum().sum()
    return f"📊 Total forecast for **{collection}**: **{int(total):,} units**."

def top_collection_for_month(month, year):
    full_month = f"{month} {year}"
    col = month_column_map.get(full_month)
    if not col or col not in df.columns:
        return f"⚠️ No forecast data for {full_month}."
    grouped = df.groupby("Style Collection")[col].sum().reset_index()
    top = grouped.sort_values(by=col, ascending=False).iloc[0]
    return f"🏆 Top collection in **{full_month}**: **{top['Style Collection']}** with **{int(top[col]):,} units**."

def top_3_styles(collection, month, year):
    full_month = f"{month} {year}"
    col = month_column_map.get(full_month)
    filtered = df[df["Style Collection"].str.lower() == collection.lower()]
    if filtered.empty or col not in df.columns:
        st.warning("No data.")
        return
    top = filtered.sort_values(by=col, ascending=False).head(3)
    top["Label"] = top["Style Number"].astype(str) + " – " + top["Description"]
    st.subheader(f"🏅 Top 3 styles in {collection} for {full_month}")
    st.bar_chart(top.set_index("Label")[col])
    st.dataframe(top[["Style Number", "Description", col]])
    csv = top[["Style Number", "Description", col]].to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download CSV", csv, file_name=f"top_styles_{collection}_{month}_{year}.csv")

def month_to_month_change(collection):
    cols = list(month_column_map.values())
    filtered = df[df["Style Collection"].str.lower() == collection.lower()]
    if filtered.empty:
        return f"⚠️ No data for '{collection}'."
    totals = filtered[cols].sum()
    diffs = totals.diff().fillna(0)
    output = [f"📈 **{m}**: Δ {int(diffs[c]):,} units" for m, c in month_column_map.items()]
    return f"📊 Month-over-month change for **{collection}**:\n\n" + "\n".join(output)

def chart_forecast(collection):
    cols = list(month_column_map.values())
    filtered = df[df["Style Collection"].str.lower() == collection.lower()]
    if filtered.empty:
        st.warning(f"No data for '{collection}'.")
        return
    totals = filtered[cols].sum()
    plt.figure(figsize=(8, 4))
    plt.plot(list(month_column_map.keys()), totals.values, marker='o')
    plt.title(f"Forecast Trend for {collection}")
    plt.xlabel("Month")
    plt.ylabel("Units")
    plt.grid(True)
    st.pyplot(plt)

def compare_collections(collection1, collection2, month, year):
    full_month = f"{month} {year}"
    col = month_column_map.get(full_month)
    if not col or col not in df.columns:
        return f"⚠️ Invalid month."
    df1 = df[df["Style Collection"].str.lower() == collection1.lower()]
    df2 = df[df["Style Collection"].str.lower() == collection2.lower()]
    sum1 = df1[col].sum() if not df1.empty else 0
    sum2 = df2[col].sum() if not df2.empty else 0
    return (
        f"📊 Forecast comparison for **{full_month}**:\n\n"
        f"- **{collection1}**: {int(sum1):,} units\n"
        f"- **{collection2}**: {int(sum2):,} units\n\n"
        f"📈 {'🔼' if sum1 > sum2 else '🔽'} **{'{0} leads'.format(collection1) if sum1 > sum2 else '{0} leads'.format(collection2)}**"
    )

def export_color_breakdown(collection):
    cols = list(month_column_map.values())
    filtered = df[df["Style Collection"].str.lower() == collection.lower()]
    if filtered.empty:
        st.warning(f"No data for '{collection}'.")
        return
    color_summary = filtered.groupby("Color")[cols].sum()
    color_summary["Total"] = color_summary.sum(axis=1)
    color_summary = color_summary.sort_values(by="Total", ascending=False)
    st.subheader(f"🎨 Color Breakdown for {collection}")
    st.dataframe(color_summary)

    csv = color_summary.reset_index().to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Color Breakdown CSV",
        data=csv,
        file_name=f"color_breakdown_{collection}.csv",
        mime="text/csv"
    )

# ---- OpenAI Function Schema ----
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
        "description": "Get collection with highest forecast",
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
        "description": "Get MoM change for a collection",
        "parameters": {
            "type": "object",
            "properties": {"collection": {"type": "string"}},
            "required": ["collection"]
        }
    },
    {
        "name": "chart_forecast",
        "description": "Show a chart for a collection",
        "parameters": {
            "type": "object",
            "properties": {"collection": {"type": "string"}},
            "required": ["collection"]
        }
    },
    {
        "name": "compare_collections",
        "description": "Compare forecasts between two collections",
        "parameters": {
            "type": "object",
            "properties": {
                "collection1": {"type": "string"},
                "collection2": {"type": "string"},
                "month": {"type": "string"},
                "year": {"type": "integer"}
            },
            "required": ["collection1", "collection2", "month", "year"]
        }
    },
    {
        "name": "export_color_breakdown",
        "description": "Show and download color breakdown for a collection",
        "parameters": {
            "type": "object",
            "properties": {"collection": {"type": "string"}},
            "required": ["collection"]
        }
    }
]

# ---- User Question Input ----
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
                    case "month_to_month_change":
                        st.success(month_to_month_change(**args))
                    case "chart_forecast":
                        chart_forecast(**args)
                    case "compare_collections":
                        st.success(compare_collections(**args))
                    case "export_color_breakdown":
                        export_color_breakdown(**args)
            else:
                st.success(msg["content"])
        except Exception as e:
            st.error(f"❌ Error: {e}")








