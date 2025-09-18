import streamlit as st
import pandas as pd
import openai
import json

# Set your OpenAI API key (Streamlit will load it from the secrets tab on the web)
openai.api_key = st.secrets["OPENAI_API_KEY"]

# File name of your Excel sheet
DATA_FILE = "Big4RollingForecast.xlsx"

# Function to get the forecast
def forecast_lookup(collection: str, month: str, year: int) -> str:
    df = pd.read_excel(DATA_FILE)

    # Map month-year combinations to column names
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

    # Filter for the selected collection
    filtered_df = df[df["Style Collection"].str.strip().str.lower() == collection.lower()]

    # Sum the forecasted demand
    total = filtered_df[target_column].sum()

    return f"📊 Forecasted demand for **{collection}** in **{full_month}** is: **{total:,} units**."

# Define function schema for OpenAI
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

# Build the Streamlit app interface
st.set_page_config(page_title="SupplyKai Forecast Assistant 🤖", layout="centered")
st.title("📦 SupplyKai Forecast Assistant")
st.caption("Ask a question like: *'What is the forecast for Accolade in September 2026?'*")

user_question = st.text_input("💬 Ask your forecast question:")

if user_question:
    with st.spinner("Thinking..."):
        response = openai.ChatCompletion.create(
            model="gpt-4",
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
