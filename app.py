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

# ---- Forecast Lookup Function ----
def forecast_lookup(collection: str, month: str, year: int) -> str:
    # Map month-year combinations to column names in your dataset
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
        return f"⚠️ Sorry, no forecast data available for {full_month}."

    target_column = month_column_map[full_month]

    if target_column not in df.columns:
        return f"⚠️ The column '{target_column}' is missing from the uploaded file."

    # Filter for the specified style collection
    filtered_df = df[df["Style Collection"].str.strip().str.lower() == collection.lower()]

    if filtered_df.empty:
        return f"⚠️ No data found for the collection '{collection}'."

    # Sum the forecasted units
    total = filtered_df[target_column].sum()

    return f"📊 Forecasted demand for **{collection}** in **{full_month}** is: **{total:,} units**."

# ---- Define Function Schema for OpenAI ----
functions = [
    {
        "name": "forecast_lookup",
        "description": "Get forecasted demand for a specific style collection and month",
        "parameters": {
            "type": "object",
            "properties": {
                "collection": {
                    "type": "string",
                    "description": "Style collection name, e.g. 'Accolade'"
                },
                "month": {
                    "type": "string",
                    "description": "Full month name, e.g. 'September'"
                },
                "year": {
                    "type": "integer",
                    "description": "Year, e.g. 2026"
                }
            },
            "required": ["collection", "month", "year"]
        }
    }
]

# ---- User Question Input ----
user_question = st.text_input("💬 Ask your forecast question:")

if user_question:
    with st.spinner("Thinking..."):
        try:
            # Ask OpenAI to interpret the question and call the correct function
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "user", "content": user_question}
                ],
                functions=functions,
                function_call="auto"
            )

            message = response.choices[0].message

            if message.get("function_call"):
                args = json.loads(message["function_call"]["arguments"])
                answer = forecast_lookup(**args)
            else:
                answer = message["content"]

            st.success(answer)

        except Exception as e:
            st.error(f"An error occurred while processing your question: {e}")
