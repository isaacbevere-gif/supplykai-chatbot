import streamlit as st
import pandas as pd
import openai
import json

# ---- App Configuration ----
st.set_page_config(page_title="SupplyKai Forecast Assistant 🤖", layout="centered")
st.title("📦 SupplyKai Forecast Assistant")
st.caption("Upload your forecast file and ask natural questions about forecasted demand.")

# ---- Load OpenAI API Key from Streamlit Secrets ----
openai.api_key = st.secrets["OPENAI_API_KEY"]

# ---- File Upload ----
uploaded_file = st.file_uploader("📁 Upload your Big4RollingForecast.xlsx", type=["xlsx"])

if uploaded_file is None:
    st.warning("Please upload your forecast Excel file to continue.")
    st.stop()

# ---- Load Excel Data ----
try:
    df = pd.read_excel(uploaded_file)
except Exception as e:
    st.error(f"Failed to read the Excel file: {e}")
    st.stop()

# ---- Forecast Lookup (Specific Month) ----
def forecast_lookup(collection: str, month: str, year: int) -> str:
    month_column_map = {
        "April 2026": "SU26 M1",
        "May 2026": "SU26 M2",
        "June 2026": "SU26 M3",
        "July 2026": "FAL26 M1",
        "August 2026": "FAL26 M2",
        "September 2026": "FAL26 M3"
    }

    full_month = f"{month} {year}"
    if full_month not in month_column_map:
        return f"⚠️ Sorry, no for
