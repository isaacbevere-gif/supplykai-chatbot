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
        return f"⚠️ Sorry, no forecast data available for {full_month}."

    target_column = month_column_map[full_month]

    if target_column not in df.columns:
        return f"⚠️ The column '{target_column}' is missing from the uploaded file."

    filtered_df = df[df["Style Collection"].str.strip().str.lower() == collection.lower()]

    if filtered_df.empty:
        return f"⚠️ No data found for the collection '{collection}'."

    total = filtered_df[target_column].sum()

    return f"📊 Forecasted demand for **{collection}** in **{full_month}** is: **{int(total):,} units**."

# ---- Total Forecast Across All Months ----
def total_forecast_for_collection(collection: str) -> str:
    forecast_columns = [
        "SU26 M1", "SU26 M2", "SU26 M3",
        "FAL26 M1", "FAL26 M2", "FAL26 M3"
    ]

    missing_cols = [col for col in forecast_columns if col not in df.columns]
    if missing_cols:
        return f"⚠️ Missing columns in file: {', '.join(missing_cols)}"

    filtered_df = df[df["Style Collection"].str.strip().str.lower() == collection.lower()]

    if filtered_df.empty:
        return f"⚠️ No data found for the collection '{collection}'."

    total = filtered_df[forecast_columns].sum().sum()

    return f"📊 Total forecast for **{collection}** across all months is: **{int(total):,} units**."

# ---- Top Collection in a Given Month ----
def top_collection_for_month(month: str, year: int) -> str:
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

    grouped = df.groupby("Style Collection")[target_column].sum().reset_index()

    if grouped.empty:
        return "⚠️ No collections found in the data."

    top_row = grouped.sort_values(by=target_column, ascending=False).iloc[0]

    top_collection = top_row["Style Collection"]
    top_value = int(top_row[target_column])

    return f"🏆 The collection with the highest forecast in **{full_month}** is **{top_collection}** with **{top_value:,} units**."

# ---- Define Functions for OpenAI ----
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
    },
    {
        "name": "total_forecast_for_collection",
        "description": "Get the total forecasted demand for a collection across all months",
        "parameters": {
            "type": "object",
            "properties": {
                "collection": {
                    "type": "string",
                    "description": "Style collection name, e.g. 'Accolade'"
                }
            },
            "required": ["collection"]
        }
    },
    {
        "name": "top_collection_for_month",
        "description": "Find the collection with the highest forecast in a specific month",
        "parameters": {
            "type": "object",
            "properties": {
                "month": {
                    "type": "string",
                    "description": "Full month name, e.g. 'September'"
                },
                "year": {
                    "type": "integer",
                    "description": "Year, e.g. 2026"
                }
            },
            "required": ["month", "year"]
        }
    }
]

# ---- User Question Input ----
user_question = st.text_input("💬 Ask your forecast question:")

if user_question:
    with st.spinner("Thinking..."):
        try:
            # Call OpenAI to interpret the user's question
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": user_question}],
                functions=functions,
                function_call="auto"
            )

            message = response.choices[0].message

            if message.get("function_call"):
                function_name = message["function_call"]["name"]
                args = json.loads(message["function_call"]["arguments"])

                if function_name == "forecast_lookup":
                    answer = forecast_lookup(**args)
                elif function_name == "total_forecast_for_collection":
                    answer = total_forecast_for_collection(**args)
                elif function_name == "top_collection_for_month":
                    answer = top_collection_for_month(**args)
                else:
                    answer = f"⚠️ Function '{function_name}' is not implemented."
            else:
                answer = message["content"]

            st.success(answer)

        except Exception as e:
            st.error(f"An error occurred while processing your question:\n\n{e}")


            st.success(answer)

        except Exception as e:
            st.error(f"An error occurred while processing your question:\n\n{e}")

