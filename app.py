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
st.set_page_config(page_title="SupplyKai Assistant v.02", layout="centered")

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
st.title("SupplyKai Assistant v.02")
st.caption("Upload your unified dataset and ask domain-specific questions.")

# ---- OPENAI API KEY ----
openai.api_key = st.secrets["OPENAI_API_KEY"]

# ---- FILE UPLOAD ----
uploaded_file = st.file_uploader("📁 Upload your dataset (Products_Master.csv or .xlsx)", type=["csv", "xlsx"])
if uploaded_file is None:
    st.warning("Please upload a dataset.")
    st.stop()

try:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
except Exception as e:
    st.error(f"Error reading file: {e}")
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

# ---- EXISTING FORECAST FUNCTIONS ----
def list_available_collections():
    if "Style Collection" not in df.columns:
        return "⚠️ 'Style Collection' column not found."
    collections = df["Style Collection"].dropna().unique()
    collections = sorted([str(c).strip() for c in collections])
    return "Available collections:\n\n" + "\n".join(f"- {c}" for c in collections)

# ---- NEW FUNCTIONS (Unified Dataset) ----
def pending_lab_dips():
    if "Lab_Dip_Status" not in df.columns:
        return "⚠️ 'Lab_Dip_Status' column not found."
    pending = df[df["Lab_Dip_Status"].str.lower() == "pending"]
    if pending.empty:
        return "✅ All lab dips are approved."
    return pending[["Style", "Product_Description", "Fabric", "Style Vendor", "Lab_Dip_Status"]]

def raw_material_expiry_risks():
    if "RM_Shelf_Life_End" not in df.columns:
        return "⚠️ 'RM_Shelf_Life_End' column not found."
    today = pd.Timestamp.today()
    risks = df[pd.to_datetime(df["RM_Shelf_Life_End"], errors="coerce") < today + pd.Timedelta(days=30)]
    if risks.empty:
        return "✅ No raw materials expiring within 30 days."
    return risks[["Style", "Product_Description", "Category", "RM_Shelf_Life_End", "Compliance_Flag", "Notes"]]

def sustainable_fabrics(min_percent=50):
    if "Sustainability_Flag" not in df.columns:
        return "⚠️ 'Sustainability_Flag' column not found."
    mask = df["Sustainability_Flag"].str.extract(r"(\d+)", expand=False).astype(float)
    sustainable = df[mask.fillna(0) >= min_percent]
    if sustainable.empty:
        return f"⚠️ No fabrics above {min_percent}% recycled content."
    return sustainable[["Style", "Product_Description", "Fabric", "Sustainability_Flag", "Style Vendor"]]

# ---- OPENAI FUNCTIONS ----
functions = [
    {
        "name": "list_available_collections",
        "description": "List all unique collections from the uploaded file",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "pending_lab_dips",
        "description": "List all styles with pending lab dip approvals",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "raw_material_expiry_risks",
        "description": "Identify raw materials expiring soon",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "sustainable_fabrics",
        "description": "Show fabrics with sustainability above a threshold",
        "parameters": {
            "type": "object",
            "properties": {"min_percent": {"type": "integer"}},
            "required": []
        }
    }
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
                        st.success(list_available_collections())
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

































