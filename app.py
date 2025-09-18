import streamlit as st
import pandas as pd
import openai
import json
import os
import matplotlib.pyplot as plt
import base64
import io
import re

# ---- PAGE CONFIG ----
st.set_page_config(page_title="SupplyKai Lite v.07", layout="centered")

# ---- LOGO ----
def show_logo():
    logo_path = "supplykai_logo.png.png"
    if os.path.exists(logo_path):
        st.markdown(
            f"""
            <div style="display: flex; justify-content: center; padding-bottom: 10px;">
                <img src="data:image/png;base64,{base64.b64encode(open(logo_path, "rb").read()).decode()}" width="200">
            </div>
            """,
            unsafe_allow_html=True
        )

show_logo()

# ---- TITLE ----
st.title("SupplyKai Lite v.07")
st.caption("Upload your Forecast (Excel) and Master (CSV) datasets, then ask domain-specific questions.")

# ---- OPENAI API KEY ----
openai.api_key = st.secrets["OPENAI_API_KEY"]

# ---- HELPERS ----
def canonicalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercase, trim, and replace any non-alphanumeric with underscores."""
    df = df.copy()
    new_cols = []
    for c in df.columns.astype(str):
        c2 = c.strip()
        c2 = c2.replace("\u00A0", " ")  # non-breaking space
        c2 = c2.lower()
        c2 = re.sub(r"[^a-z0-9]+", "_", c2)  # replace non-alphanum
        c2 = c2.strip("_")
        new_cols.append(c2)
    df.columns = new_cols
    return df

def ensure_dataframe(obj, fallback_message):
    """Always return a DataFrame so Streamlit never crashes on strings."""
    if isinstance(obj, pd.DataFrame):
        return obj
    return pd.DataFrame({"Message": [fallback_message]})

# ---- FILE UPLOADS ----
st.subheader("📂 Upload Data Files")
uploaded_master = st.file_uploader("Upload Master Dataset (CSV)", type=["csv"])
uploaded_forecast = st.file_uploader("Upload Forecast Dataset (Excel)", type=["xlsx"])

if not uploaded_master or not uploaded_forecast:
    st.warning("Please upload both a Master CSV and a Forecast Excel file.")
    st.stop()

# ---- READ & NORMALIZE FILES ----
try:
    # FIX: auto-detect delimiter for CSV
    df_master_raw = pd.read_csv(uploaded_master, sep=None, engine="python")
    df_master = canonicalize_columns(df_master_raw)
except Exception as e:
    st.error(f"Error reading Master CSV: {e}")
    st.stop()

try:
    df_forecast_raw = pd.read_excel(uploaded_forecast)
    df_forecast = canonicalize_columns(df_forecast_raw)
except Exception as e:
    st.error(f"Error reading Forecast Excel: {e}")
    st.stop()

# ---- OPTIONAL PREVIEW ----
with st.expander("🔎 Data preview & column inspector"):
    st.markdown("**Master columns (normalized):**")
    st.write(list(df_master.columns))
    st.dataframe(df_master.head())
    st.markdown("---")
    st.markdown("**Forecast columns (normalized):**")
    st.write(list(df_forecast.columns))
    st.dataframe(df_forecast.head())

# ---- MONTH COLUMN MAPPING ----
month_column_map = {
    "April 2026": "su26_m1",
    "May 2026": "su26_m2",
    "June 2026": "su26_m3",
    "July 2026": "fal26_m1",
    "August 2026": "fal26_m2",
    "September 2026": "fal26_m3"
}

# ---- FORECAST FUNCTIONS ----
def list_available_collections():
    col = "style_collection"
    if col not in df_forecast.columns:
        return pd.DataFrame({"Message": [f"⚠️ '{col}' column not found in forecast file. Found: {', '.join(df_forecast.columns)}"]})
    collections = df_forecast[col].dropna().astype(str).str.strip().unique()
    collections = sorted(collections)
    return pd.DataFrame({"available_collections": collections})

def forecast_lookup(collection, month, year, color=None):
    coll_col = "style_collection"
    color_col = "color"
    if coll_col not in df_forecast.columns:
        return pd.DataFrame({"Message": [f"⚠️ '{coll_col}' column not found."]})
    col = month_column_map.get(f"{month} {year}")
    if not col or col not in df_forecast.columns:
        return pd.DataFrame({"Message": [f"⚠️ No forecast column for {month} {year}."]})

    filtered = df_forecast[df_forecast[coll_col].astype(str).str.lower().str.strip() == collection.lower().strip()]
    if color and color_col in df_forecast.columns:
        filtered = filtered[filtered[color_col].astype(str).str.lower().str.strip() == color.lower().strip()]

    if filtered.empty:
        return pd.DataFrame({"Message": [f"⚠️ No data for {collection} in {month} {year}."]})

    total = pd.to_numeric(filtered[col], errors="coerce").fillna(0).sum()
    return pd.DataFrame({"collection": [collection], "month": [f"{month} {year}"], "total_units": [int(total)]})

def top_3_styles(collection, month, year, color=None):
    coll_col = "style_collection"
    color_col = "color"
    style_col = "style_number" if "style_number" in df_forecast.columns else "style"
    desc_col = "description" if "description" in df_forecast.columns else "product_description"

    col = month_column_map.get(f"{month} {year}")
    if not col or col not in df_forecast.columns:
        return pd.DataFrame({"Message": [f"⚠️ No forecast column for {month} {year}."]})

    filtered = df_forecast[df_forecast[coll_col].astype(str).str.lower().str.strip() == collection.lower().strip()]
    if color and color_col in df_forecast.columns:
        filtered = filtered[filtered[color_col].astype(str).str.lower().str.strip() == color.lower().strip()]
    if filtered.empty:
        return pd.DataFrame({"Message": [f"⚠️ No data for {collection} in {month} {year}."]})

    filtered[col] = pd.to_numeric(filtered[col], errors="coerce").fillna(0)
    top = filtered.sort_values(by=col, ascending=False).head(3)
    return top[[style_col, desc_col, color_col, col]].rename(columns={
        style_col: "style_number",
        desc_col: "description",
        color_col: "color",
        col: col
    })

def color_performance_for_style(style_number):
    style_col = "style_number" if "style_number" in df_forecast.columns else "style"
    color_col = "color"
    cols = [c for c in month_column_map.values() if c in df_forecast.columns]
    if not cols:
        return pd.DataFrame({"Message": ["⚠️ No monthly forecast columns found in forecast file."]})

    filtered = df_forecast[df_forecast[style_col].astype(str).str.strip() == str(style_number).strip()]
    if filtered.empty:
        return pd.DataFrame({"Message": [f"⚠️ No data for style {style_number}."]})

    for c in cols:
        filtered[c] = pd.to_numeric(filtered[c], errors="coerce").fillna(0)

    grouped = filtered.groupby(color_col)[cols].sum()
    grouped["total_units"] = grouped.sum(axis=1)
    grouped = grouped.sort_values("total_units", ascending=False)
    return grouped.reset_index()

# ---- MASTER FUNCTIONS ----
def pending_lab_dips():
    if "lab_dip_status" not in df_master.columns:
        return pd.DataFrame({"Message": [f"⚠️ 'lab_dip_status' column not found in master file. Found: {', '.join(df_master.columns)}"]})
    pending = df_master[df_master["lab_dip_status"].astype(str).str.lower().str.strip() == "pending"]
    if pending.empty:
        return pd.DataFrame({"Message": ["✅ All lab dips are approved."]})
    return pending[[c for c in ["style", "product_description", "fabric", "style_vendor", "lab_dip_status"] if c in df_master.columns]]

def raw_material_expiry_risks():
    date_col = "rm_shelf_life_end"
    if date_col not in df_master.columns:
        return pd.DataFrame({"Message": [f"⚠️ '{date_col}' column not found in master file. Found: {', '.join(df_master.columns)}"]})
    
    today = pd.Timestamp.today()
    # Force text cleanup
    dates_raw = df_master[date_col].astype(str).str.strip().replace({"nan": None, "n/a": None, "NaT": None, "—": None})
    # Parse with flexible format inference
    dates = pd.to_datetime(dates_raw, errors="coerce", infer_datetime_format=True)

    # Debugging
    st.write("🔎 Cleaned raw values:", dates_raw.head(10))
    st.write("🔎 Parsed datetime values:", dates.head(10))

    risks = df_master[(dates.notna()) & (dates < (today + pd.Timedelta(days=30)))]
    if risks.empty:
        return pd.DataFrame({"Message": ["✅ No raw materials expiring within 30 days."]})
    
    return risks[[c for c in ["style", "product_description", "category", date_col, "compliance_flag", "notes"] if c in df_master.columns]]

def sustainable_fabrics(min_percent=50):
    col = "sustainability_flag"
    if col not in df_master.columns:
        return pd.DataFrame({"Message": [f"⚠️ '{col}' column not found in master file. Found: {', '.join(df_master.columns)}"]})
    pct = df_master[col].astype(str).str.extract(r"(\d+)", expand=False).astype(float)
    sustainable = df_master[pct.fillna(0) >= float(min_percent)]
    if sustainable.empty:
        return pd.DataFrame({"Message": [f"⚠️ No fabrics above {min_percent}% recycled content."]})
    return sustainable[[c for c in ["style", "product_description", "fabric", col, "style_vendor"] if c in df_master.columns]]

# ---- OPENAI FUNCTIONS ----
functions = [
    {"name": "list_available_collections", "description": "List all unique collections", "parameters": {"type": "object", "properties": {}}},
    {"name": "forecast_lookup", "description": "Get forecast for a collection and month", "parameters": {"type": "object","properties": {"collection": {"type": "string"},"month": {"type": "string"},"year": {"type": "integer"},"color": {"type": "string"}}, "required": ["collection", "month", "year"]}},
    {"name": "top_3_styles", "description": "Top 3 styles in a collection for a month", "parameters": {"type": "object","properties": {"collection": {"type": "string"},"month": {"type": "string"},"year": {"type": "integer"},"color": {"type": "string"}}, "required": ["collection", "month", "year"]}},
    {"name": "color_performance_for_style", "description": "Show color-level forecast for a style number", "parameters": {"type": "object","properties": {"style_number": {"type": "string"}}, "required": ["style_number"]}},
    {"name": "pending_lab_dips", "description": "List all styles with pending lab dip approvals", "parameters": {"type": "object", "properties": {}}},
    {"name": "raw_material_expiry_risks", "description": "Identify raw materials expiring soon", "parameters": {"type": "object", "properties": {}}},
    {"name": "sustainable_fabrics", "description": "Show fabrics with sustainability above a threshold", "parameters": {"type": "object","properties": {"min_percent": {"type": "integer"}}, "required": []}}
]

# ---- CHAT INTERFACE ----
user_question = st.text_input("💬 Ask your supply chain question:")

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
                    case "list_available_collections":
                        st.dataframe(ensure_dataframe(list_available_collections(), "No collections found."))
                    case "forecast_lookup":
                        st.dataframe(ensure_dataframe(forecast_lookup(**args), "No forecast found."))
                    case "top_3_styles":
                        st.dataframe(ensure_dataframe(top_3_styles(**args), "No styles found."))
                    case "color_performance_for_style":
                        st.dataframe(ensure_dataframe(color_performance_for_style(**args), "No color performance found."))
                    case "pending_lab_dips":
                        st.dataframe(ensure_dataframe(pending_lab_dips(), "No pending lab dips."))
                    case "raw_material_expiry_risks":
                        st.dataframe(ensure_dataframe(raw_material_expiry_risks(), "No RM expiry risks."))
                    case "sustainable_fabrics":
                        min_percent = args.get("min_percent", 50)
                        st.dataframe(ensure_dataframe(sustainable_fabrics(min_percent), "No sustainable fabrics found."))
            else:
                st.success(msg["content"])
        except Exception as e:
            st.error(f"❌ Error: {e}")
