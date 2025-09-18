import streamlit as st
import pandas as pd
import openai
import json
from PIL import Image
import os
import matplotlib.pyplot as plt
import base64
import io

# ---- CONFIG ----
st.set_page_config(page_title="SupplyKai Assistant v.01", page_icon=None, layout="centered")

# ---- BACKGROUND IMAGE (JPEG) ----
def set_background():
    file_path = "supplykai_background_image.jpg"
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        st.markdown(
            f"""
            <style>
            .stApp {{
                background-image: url("data:image/jpg;base64,{encoded}");
                background-size: cover;
                background-repeat: no-repeat;
                background-attachment: fixed;
                background-position: center;
            }}
            </style>
            """,
            unsafe_allow_html=True
        )

# ---- CUSTOM STYLES (Proxima Soft, black text, white input) ----
def set_custom_styles():
    st.markdown(
        """
        <style>

        /* GLOBAL FONT + TEXT COLOR */
        html, body, .stApp {
            font-family: "Proxima Soft", "Avenir", "Helvetica Neue", sans-serif !important;
            color: black !important;
        }

        /* CAPTION TEXT UNDER TITLE */
        .stMarkdown h6, .stCaption {
            color: black !important;
            font-weight: normal !important;
        }

        /* FILE UPLOADER LABEL TEXT */
        .stFileUploader label {
            color: black !important;
            font-weight: bold !important;
        }

        /* FILE UPLOADER BROWSE BUTTON */
        .stFileUploader label div span {
            background-color: white !important;
            color: black !important;
            padding: 6px 12px;
            border-radius: 5px;
            font-weight: bold !important;
            border: 1px solid #000 !important;
        }

        /* Uploaded file name preview */
        .stFileUploader .uploadedFileName {
            color: black !important;
        }

        /* INPUT BOXES */
        input[type="text"], textarea, .stTextInput input {
            background-color: white !important;
            color: black !important;
            border: 1px solid #ccc !important;
        }

        /* BUTTONS */
        .stButton > button, .stDownloadButton > button {
            color: black !important;
            background-color: white !important;
            font-weight: 500 !important;
        }

        /* WARNING TEXT */
        .stAlert {
            background-color: rgba(255, 255, 255, 0.85) !important;
            color: black !important;
            border: 1px solid #ccc !important;
        }

        </style>
        """,
        unsafe_allow_html=True
    )

# ---- RUN STYLES + LOGO ----
set_background()
set_custom_styles()
def show_logo()

st.title("SupplyKai Assistant v.01 (Big4 Monthly Rolling Forecast)")
st.caption("Upload your forecast file and ask your questions.")
# ---- OPENAI API ----
openai.api_key = st.secrets["OPENAI_API_KEY"]

# ---- FILE UPLOAD ----
uploaded_file = st.file_uploader("📁 Upload your Big4RollingForecast.xlsx", type=["xlsx"])
if uploaded_file is None:
    st.warning("Please upload a forecast file.")
    st.stop()

try:
    df = pd.read_excel(uploaded_file)
except Exception as e:
    st.error(f"Error reading file: {e}")
    st.stop()

# ---- MONTH COLUMN MAPPING ----
month_column_map = {
    "April 2026": "SU26 M1",
    "May 2026": "SU26 M2",
    "June 2026": "SU26 M3",
    "July 2026": "FAL26 M1",
    "August 2026": "FAL26 M2",
    "September 2026": "FAL26 M3"
}

# ---- VALIDATION: CHECK IF COLLECTION EXISTS ----
def is_valid_collection(collection):
    available = df["Style Collection"].dropna().str.lower().str.strip().unique()
    return collection.lower().strip() in available

# ---- LIST ALL COLLECTIONS ----
def list_available_collections():
    if "Style Collection" not in df.columns:
        return "⚠️ 'Style Collection' column not found."
    collections = df["Style Collection"].dropna().unique()
    collections = sorted([str(c).strip() for c in collections])
    return "Available collections:\n\n" + "\n".join(f"- {c}" for c in collections)
# ---- EXPORT ANY DATAFRAME TO PDF ----
def export_table_to_pdf(dataframe, title):
    from matplotlib.backends.backend_pdf import PdfPages
    fig, ax = plt.subplots(figsize=(8.5, 3 + len(dataframe) * 0.5))
    ax.axis("off")
    table = ax.table(cellText=dataframe.values, colLabels=dataframe.columns, loc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    plt.title(title, fontsize=12)
    output = io.BytesIO()
    with PdfPages(output) as pdf:
        pdf.savefig(fig, bbox_inches='tight')
    output.seek(0)
    return output

# ---- FORECAST LOOKUP ----
def forecast_lookup(collection, month, year, color=None):
    if not is_valid_collection(collection):
        return list_available_collections()
    col = month_column_map.get(f"{month} {year}")
    filtered = df[df["Style Collection"].str.lower().str.strip() == collection.lower().strip()]
    if color:
        filtered = filtered[filtered["Color"].str.lower().str.strip() == color.lower().strip()]
    if not col or col not in df.columns or filtered.empty:
        return f"⚠️ No data for {collection} in {month} {year}."
    total = filtered[col].sum()
    label = f"{collection} in {month} {year}"
    if color:
        label += f" (Color: {color})"
    return f"📊 Forecast for **{label}**: **{int(round(total)):,} units**."

# ---- TOP 3 STYLES ----
def top_3_styles(collection, month, year, color=None):
    if not is_valid_collection(collection):
        st.warning(list_available_collections())
        return
    col = month_column_map.get(f"{month} {year}")
    filtered = df[df["Style Collection"].str.lower().str.strip() == collection.lower().strip()]
    if color:
        filtered = filtered[filtered["Color"].str.lower().str.strip() == color.lower().strip()]
    if not col or col not in df.columns or filtered.empty:
        st.warning(f"⚠️ No data for {collection} in {month} {year}.")
        return
    top = filtered.sort_values(by=col, ascending=False).head(3)
    top["Label"] = top["Style Number"].astype(str) + " – " + top["Description"]
    values = top[col].round().astype(int).values
    labels = top["Label"].values

    st.subheader(f"Top 3 styles in {collection} for {month} {year}" + (f" (Color: {color})" if color else ""))
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(labels, values, color="#1f77b4")
    ax.set_ylim(0, max(values) * 1.2)
    ax.set_ylabel("Units")
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + max(values) * 0.05, f"{value:,}", ha="center", fontsize=10)
    plt.xticks(rotation=0)
    plt.tight_layout()
    st.pyplot(fig)

    table = top[["Style Number", "Description", col]]
    st.dataframe(table)

    csv = table.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download CSV", csv, file_name="top_styles.csv")

    pdf = export_table_to_pdf(table, f"Top 3 Styles – {collection} – {month} {year}")
    st.download_button("📄 Download PDF", data=pdf, file_name="top_styles.pdf", mime="application/pdf")

# ---- COLOR PERFORMANCE BY STYLE ----
def color_performance_for_style(style_number):
    cols = list(month_column_map.values())
    filtered = df[df["Style Number"].astype(str).str.lower().str.strip() == style_number.lower().strip()]
    if filtered.empty:
        st.warning(f"No data for style {style_number}.")
        return
    grouped = filtered.groupby("Color")[cols].sum()
    grouped["Total Units"] = grouped.sum(axis=1)
    grouped = grouped.sort_values("Total Units", ascending=False)
    st.subheader(f"Color Performance for Style {style_number}")
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
    st.download_button("📥 Download CSV", csv, file_name="color_performance.csv")

    pdf = export_table_to_pdf(grouped.reset_index(), f"Color Performance – Style {style_number}")
    st.download_button("📄 Download PDF", data=pdf, file_name="color_performance.pdf", mime="application/pdf")
# ---- OPENAI FUNCTION SCHEMA ----
functions = [
    {
        "name": "forecast_lookup",
        "description": "Get forecast for a collection and month, optionally filtered by color",
        "parameters": {
            "type": "object",
            "properties": {
                "collection": {"type": "string"},
                "month": {"type": "string"},
                "year": {"type": "integer"},
                "color": {"type": "string"}
            },
            "required": ["collection", "month", "year"]
        }
    },
    {
        "name": "top_3_styles",
        "description": "Top 3 styles in a collection for a month, optionally filtered by color",
        "parameters": {
            "type": "object",
            "properties": {
                "collection": {"type": "string"},
                "month": {"type": "string"},
                "year": {"type": "integer"},
                "color": {"type": "string"}
            },
            "required": ["collection", "month", "year"]
        }
    },
    {
        "name": "color_performance_for_style",
        "description": "Show color-level forecast for a style number",
        "parameters": {
            "type": "object",
            "properties": {
                "style_number": {"type": "string"}
            },
            "required": ["style_number"]
        }
    },
    {
        "name": "list_available_collections",
        "description": "List all unique collections from the uploaded file",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
]

# ---- USER INPUT & OPENAI COMPLETION ----
user_question = st.text_input("💬 Ask your forecast question:")

if user_question:
    with st.spinner("Thinking..."):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "user", "content": user_question}
                ],
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
                    case "top_3_styles":
                        top_3_styles(**args)
                    case "color_performance_for_style":
                        color_performance_for_style(**args)
                    case "list_available_collections":
                        st.success(list_available_collections())
            else:
                st.success(msg["content"])

        except Exception as e:
            st.error(f"❌ Error: {e}")
























