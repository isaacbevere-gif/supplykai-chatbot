import streamlit as st
import pandas as pd
import openai
import json
import os
import matplotlib.pyplot as plt
import base64
import io

# ---- PAGE CONFIG ----
st.set_page_config(page_title="SupplyKai Assistant v.04", layout="centered")

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
st.title("SupplyKai Assistant v.04")
st.caption("Upload your Forecast (Excel) and Master (CSV) datasets, then ask domain-specific questions.")

# ---- OPENAI API KEY ----
openai.api_key = st.secrets["OPENAI_API_KEY"]

# ---- FILE UPLOADS ----
st.subheader("📂 Upload Data Files")
uploaded_master = st.file_uploader("Upload Master Dataset (CSV)", type=["csv"])
uploaded_forecast = st.file_uploader("Upload Forecast Dataset (Excel)", type=["xlsx"])

if not uploaded_master or not uploaded_forecast:
    st.warning("Please upload both a Master CSV and a Forecast Excel file.")
    st.stop()

# ---- READ MASTER FILE ----
try:
    df_master = pd.read_csv(uploaded_master)
    # Normalize column names
    df_master.columns = (
        df_master.columns.str.strip()
        .str.replace(" ", "_")
        .str.replace("-", "_")
    )
except Exception as e:
    st.error(f"Error reading Master CSV: {e}")
    st.stop()

# ---- READ FORECAST FILE ----
try:
    df_forecast = pd.read_excel(uploaded_forecast)
    df_forecast.columns = (
        df_forecast.columns.str.strip()
        .str.replace(" ", "_")
        .str.replace("-", "_")
    )
except Exception as e:
    st.error(f"Error reading Forecast Excel: {e}")
    st.stop()

# ---- EXPORT TO PDF ----
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

# ---- MONTH COLUMN MAPPING ----
month_column_map = {
    "April 2026": "SU26_M1",
    "May 2026": "SU26_M2",
    "June 2026": "SU26_M3",
    "July 2026": "FAL26_M1",
    "August 2026": "FAL26_M2",
    "September 2026": "FAL26_M3"
}

# ---- FORECAST FUNCTIONS ----
def list_available_collections():
    if "Style_Collection" not in df_forecast.columns:
        return pd.DataFrame({"Message": ["⚠️ 'Style_Collection' column not found."]})
    collections = df_forecast["Style_Collection"].dropna().unique()
    collections = sorted([str(c).strip() for c in collections])
    return pd.DataFrame({"Available Collections": collections})

def forecast_lookup(collection, month, year, color=None):
    col = month_column_map.get(f"{month} {year}")
    if not col or col not in df_forecast.columns:
        return pd.DataFrame({"Message": [f"⚠️ No forecast column for {month} {year}."]})

    filtered = df_forecast[df_forecast["Style_Collection"].str.lower().str.strip() == collection.lower().strip()]
    if color:
        filtered = filtered[filtered["Color"].str.lower().str.strip() == color.lower().strip()]

    if filtered.empty:
        return pd.DataFrame({"Message": [f"⚠️ No data for {collection} in {month} {year}."]})

    total = filtered[col].sum()
    return pd.DataFrame({"Collection": [collection], "Month": [f"{month} {year}"], "Total Units": [int(total)]})

def top_3_styles(collection, month, year, color=None):
    col = month_column_map.get(f"{month} {year}")
    if not col or col not in df_forecast.columns:
        return pd.DataFrame({"Message": [f"⚠️ No forecast column for {month} {year}."]})

    filtered = df_forecast[df_forecast["Style_Collection"].str.lower().str.strip() == collection.lower().strip()]
    if color:
        filtered = filtered[filtered["Color"].str.lower().str.strip() == color.lower().strip()]

    if filtered.empty:
        return pd.DataFrame({"Message": [f"⚠️ No data for {collection} in {month} {year}."]})

    top = filtered.sort_values(by=col, ascending=False).head(3)
    return top[["Style_Number", "Description", "Color", col]]

def color_performance_for_style(style_number):
    cols = list(month_column_map.values())
    filtered = df_forecast[df_forecast["Style_Number"].astype(str).str.strip() == str(style_number).strip()]
    if filtered.empty:
        return pd.DataFrame({"Message": [f"⚠️ No data for style {style_number}."]})

    grouped = filtered.groupby("Color")[cols].sum()
    grouped["Total_Units"] = grouped.sum(axis=1)
    grouped = grouped.sort_values("Total_Units", ascending=False)
    return grouped.reset_index()

# ---- MASTER FUNCTIONS ----
def pending_lab_dips():
    if "Lab_Dip_Status" not in df_master.columns:
        return pd.DataFrame({"Message": ["⚠️ 'Lab_Dip_Status' column not found."]})
    pending = df_master[df_master["Lab_Dip_Status"].str.lower() == "pending"]
    if pending.empty:
        return pd.DataFrame({"Message": ["✅ All lab dips are approved."]})
    return pending[["Style", "Product_Description", "Fabric", "Style_Vendor", "Lab_Dip_Status"]]

def raw_material_expiry_risks():
    if "RM_Shelf_Life_End" not in df_master.columns:
        return pd.DataFrame({"Message": ["⚠️ 'RM_Shelf_Life_End' column not found."]})
    today = pd.Timestamp.today()
    risks = df_master[pd.to_datetime(df_master["RM_Shelf_Life_End"], errors="coerce") < today + pd.Timedelta(days=30)]
    if risks.empty:
        return pd.DataFrame({"Message": ["✅ No raw materials expiring within 30 days."]})
    return risks[["Style", "Product_Description", "Category", "RM_Shelf_Life_End", "Compliance_Flag", "Notes"]]

def sustainable_fabrics(min_percent=50):
    if "Sustainability_Flag" not in df_master.columns:
        return pd.DataFrame({"Message": ["⚠️ 'Sustainability_Flag' column not found."]})
    mask = df_master["Sustainability_Flag"].str.extract(r"(\d+)", expand=False).astype(float)
    sustainable = df_master[mask.fillna(0) >= min_percent]
    if sustainable.empty:
        return pd.DataFrame({"Message": [f"⚠️ No fabrics above {min_percent}% recycled content."]})
    return sustainable[["Style", "Product_Description", "Fabric", "Sustainability_Flag", "Style_Vendor"]]

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
                        st.dataframe(list_available_collections())
                    case "forecast_lookup":
                        st.dataframe(forecast_lookup(**args))
                    case "top_3_styles":
                        st.dataframe(top_3_styles(**args))
                    case "color_performance_for_style":
                        st.dataframe(color_performance_for_style(**args))
                    case "pending_lab_dips":
                        st.dataframe(pending_lab_dips())
                    case "raw_material_expiry_risks":
                        st.dataframe(raw_material_expiry_risks())
                    case "sustainable_fabrics":
                        min_percent = args.get("min_percent", 50)
                        st.dataframe(sustainable_fabrics(min_percent))
            else:
                st.success(msg["content"])
        except Exception as e:
            st.error(f"❌ Error: {e}")
