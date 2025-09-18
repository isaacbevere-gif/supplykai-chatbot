import streamlit as st
import pandas as pd
import openai
import json
from PIL import Image
import os
import matplotlib.pyplot as plt
import base64
import io

# ---- PAGE CONFIG ----
st.set_page_config(page_title="SupplyKai Assistant v.01", page_icon=None, layout="centered")

# ---- BACKGROUND IMAGE (JPEG) ----
def set_background():
    file_path = "supplykai_background_image.jpeg"
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        st.markdown(
            f"""
            <style>
            .stApp {{
                background-image: url("data:image/jpeg;base64,{encoded}");
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

# ---- LOGO ----
if os.path.exists("supplykai_logo.png"):
    logo = Image.open("supplykai_logo.png")
    st.image(logo, width=200)

st.title("SupplyKai Assistant v.01 (Big4 Monthly Rolling Forecast)")
st.caption("Upload your forecast file and ask your questions.")

# ---- OPENAI API KEY ----
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

# ---- MONTH COLUMN MAP ----
month_column_map = {
    "April 2026": "SU26 M1",
    "May 2026": "SU26 M2",
    "June 2026": "SU26 M3",
    "July 2026": "FAL26 M1",
    "August 2026": "FAL26 M2",
    "September 2026": "FAL26 M3"
}
# ---- Helper: Validate Collection ----
def is_valid_collection(collection):
    available = df["Style Collection"].dropna().str.lower().str.strip().unique()
    return collection.lower().strip() in available

# ---- Get Available Collections ----
def list_available_collections():
    if "Style Collection" not in df.columns:
        return "⚠️ 'Style Collection' column not found."
    collections = df["Style Collection"].dropna().unique()
    collections = sorted([str(c).strip() for c in collections])
    return "Available collections:\n\n" + "\n".join(f"- {c}" for c in collections)

# ---- Forecast Lookup with Color Filter ----
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

# ---- Export Table to PDF ----
def export_table_to_pdf(dataframe, title):
    from matplotlib.backends.backend_pdf import PdfPages
    fig, ax = plt.subplots(figsize=(8.5, 3 + len(dataframe) * 0.5))
    ax.axis("tight")
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

# ---- Top Styles (with optional color + PDF) ----
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

# ---- Color Performance (with PDF) ----
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













