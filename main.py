import streamlit as st
import os
import pdfplumber
import openai
import requests
from datetime import datetime
import io
import chardet
import http.client
import json
import urllib.parse

# Debugging function to safely check secrets
def check_secret(key):
    try:
        value = st.secrets[key]
        return f"Secret '{key}' is {'set' if value else 'empty'}"
    except Exception as e:
        return f"Error accessing secret '{key}': {str(e)}"

# Function to safely get a secret
def get_secret(key):
    try:
        return st.secrets[key]
    except Exception as e:
        st.error(f"Error accessing secret '{key}': {str(e)}")
        return None

# Set up API keys using Streamlit secrets
OPENAI_API_KEY = get_secret("OPENAI_API_KEY")
OPENCAGE_API_KEY = get_secret("OPENCAGE_API_KEY")
RAPIDAPI_KEY = get_secret("RAPIDAPI_KEY")

# Set OpenAI API key if available
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
else:
    st.warning("OpenAI API key is not set. Some features may not work.")

# Function to extract text from PDF and save as txt
def extract_and_save_text_from_pdf(file):
    try:
        file_content = file.read()
        pdf_file = io.BytesIO(file_content)
        
        text = ""
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        
        if not text.strip():
            st.warning("No text could be extracted from the PDF. It might be scanned or image-based.")
            return None, None
        
        os.makedirs("Reports", exist_ok=True)
        
        filename = f"{file.name.split('.')[0]}.txt"
        filepath = os.path.join("Reports", filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(text)
        
        return text, filepath
    except Exception as e:
        st.error(f"Error processing PDF: {str(e)}")
        return None, None

# Function to read text file
def read_text_file(file):
    content = file.read()
    detected = chardet.detect(content)
    encoding = detected['encoding']
    
    try:
        return content.decode(encoding)
    except UnicodeDecodeError:
        for enc in ['utf-8', 'latin-1', 'ascii']:
            try:
                return content.decode(enc)
            except UnicodeDecodeError:
                continue
    
    return content.decode('latin-1')

# Function to translate text
def translate_text(text, target_language):
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": f"You are a language translator. Translate the following text to {target_language}."},
            {"role": "user", "content": text}
        ]
    )
    return response.choices[0].message.content

# Function for AI QA analysis
def ai_qa_analysis(text):
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an expert analyst able to QA home inspection reports and provide feedback on any errors such as grammatical, spelling, contradictions, or possible oversights. Your goal is to improve the quality, accuracy, and readability of the home inspection report to improve the quality of the report and reduce liability."},
            {"role": "user", "content": f"Please analyze the following text and provide a summary of any errors:\n\n{text}"}
        ]
    )
    return response.choices[0].message.content

@st.cache_data
def get_property_info_from_rapidapi(address, rapidapi_key):
    if not rapidapi_key:
        return {"error": "RapidAPI key is missing. Property information is unavailable."}

    host = "realty-mole-property-api.p.rapidapi.com"
    headers = {
        'x-rapidapi-key': rapidapi_key,
        'x-rapidapi-host': host
    }

    encoded_address = urllib.parse.quote(address)

    conn = http.client.HTTPSConnection(host)
    
    try:
        conn.request("GET", f"/properties?address={encoded_address}", headers=headers)
        res = conn.getresponse()
        data = res.read()
        
        if res.status != 200:
            return {"error": f"API request failed with status code {res.status}: {data.decode('utf-8')}"}
        
        response_data = json.loads(data.decode("utf-8"))

        if response_data:
            property_info = response_data[0] if isinstance(response_data, list) else response_data
        else:
            return {"error": "No property information found for the given location."}

        return {
            "county": property_info.get('county', 'N/A'),
            "bedrooms": property_info.get('bedrooms', 'N/A'),
            "bathrooms": property_info.get('bathrooms', 'N/A'),
            "square_footage": property_info.get('squareFootage', 'N/A'),
            "year_built": property_info.get('yearBuilt', 'N/A'),
            "lot_size": property_info.get('lotSize', 'N/A'),
            "property_type": property_info.get('propertyType', 'N/A'),
            "price": property_info.get('price', 'N/A'),
            "listed_date": property_info.get('listedDate', 'N/A'),
            "address": property_info.get('formattedAddress', 'N/A'),
            "latitude": property_info.get('latitude', 'N/A'),
            "longitude": property_info.get('longitude', 'N/A')
        }

    except Exception as e:
        st.error(f"Failed to retrieve property information: {str(e)}")
        return {"error": f"Failed to retrieve property information: {str(e)}"}
    finally:
        conn.close()

def gather_info(address):
    geocode_url = f"https://api.opencagedata.com/geocode/v1/json?q={address}&key={OPENCAGE_API_KEY}"
    geocode_response = requests.get(geocode_url)
    geocode_data = geocode_response.json()
    
    if geocode_data['results']:
        lat = geocode_data['results'][0]['geometry']['lat']
        lon = geocode_data['results'][0]['geometry']['lng']

        property_info = get_property_info_from_rapidapi(address, RAPIDAPI_KEY)

        weather_url = f"https://api.weather.gov/points/{lat},{lon}"
        weather_response = requests.get(weather_url)
        if weather_response.status_code == 200:
            weather_data = weather_response.json()
            forecast_url = weather_data['properties']['forecast']
            forecast_response = requests.get(forecast_url)
            if forecast_response.status_code == 200:
                forecast_data = forecast_response.json()
                current_period = forecast_data['properties']['periods'][0]
                
                # Fetch hourly forecast to get relative humidity
                hourly_forecast_url = weather_data['properties']['forecastHourly']
                hourly_forecast_response = requests.get(hourly_forecast_url)
                if hourly_forecast_response.status_code == 200:
                    hourly_forecast_data = hourly_forecast_response.json()
                    current_hour = hourly_forecast_data['properties']['periods'][0]
                    relative_humidity = current_hour.get('relativeHumidity', {}).get('value', 'N/A')
                else:
                    relative_humidity = 'N/A'
                
                weather_info = {
                    "Temperature": f"{current_period['temperature']}°{current_period['temperatureUnit']}",
                    "Relative Humidity": f"{relative_humidity}%" if relative_humidity != 'N/A' else 'N/A',
                    "Conditions": current_period['shortForecast'],
                    "Wind": f"{current_period['windSpeed']} {current_period['windDirection']}",
                    "Forecast": current_period['detailedForecast']
                }
            else:
                weather_info = {"error": "Weather forecast data unavailable"}
        else:
            weather_info = {"error": "Weather data unavailable"}

        return property_info, weather_info
    else:
        return {"error": "Location not found"}, {"error": "Weather data unavailable"}

def create_property_report(property_info, weather_info):
    report = "# Property and Weather Report\n\n"
    
    report += "## Property Information\n"
    if isinstance(property_info, dict):
        for key, value in property_info.items():
            if key != "error":
                report += f"- **{key.replace('_', ' ').title()}:** {value}\n"
    else:
        report += f"- {property_info}\n"
    
    report += "\n## Current Weather\n"
    if isinstance(weather_info, dict):
        for key, value in weather_info.items():
            if key != "error":
                report += f"- **{key}:** {value}\n"
    else:
        report += f"- {weather_info}\n"
    
    return report

def main():
    st.title("Document Processor and Info Gatherer App")

    st.sidebar.header("Property Information")
    address = st.sidebar.text_input("Enter an address (U.S. only for weather data):")
    if st.sidebar.button("Get Info"):
        with st.spinner("Fetching property and weather information..."):
            property_info, weather_info = gather_info(address)
            st.session_state['property_info'] = property_info
            st.session_state['weather_info'] = weather_info
            st.session_state['active_tab'] = "Property & Weather Report"

    tab1, tab2, tab3 = st.tabs(["Document Upload & Translation", "AI QA Analysis", "Property & Weather Report"])

    with tab1:
        st.header("Document Upload & Translation")
        uploaded_file = st.file_uploader("Choose a file (PDF or TXT)", type=["pdf", "txt"])

        if uploaded_file is not None:
            file_type = uploaded_file.type
            if file_type == "application/pdf":
                text, filepath = extract_and_save_text_from_pdf(uploaded_file)
                if text and filepath:
                    st.success(f"PDF processed and saved as text file: {filepath}")
            elif file_type == "text/plain":
                text = read_text_file(uploaded_file)
                filepath = None
                st.success("Text file processed successfully")
            else:
                st.error("Unsupported file type. Please upload a PDF or TXT file.")
                text = None
                filepath = None
            
            if text:
                st.session_state['current_text'] = text
                st.session_state['current_filepath'] = filepath

                languages = [
                    "Spanish", "Chinese (Mandarin)", "Tagalog", "Vietnamese",
                    "Arabic", "French", "Korean", "German"
                ]
                target_language = st.selectbox("Select target language for translation", languages)

                if st.button("Translate"):
                    with st.spinner("Translating..."):
                        translated_text = translate_text(text, target_language)
                    st.subheader(f"Translated Text ({target_language}):")
                    st.text_area("", translated_text, height=300)

    with tab2:
        st.header("AI QA Analysis")
        if 'current_text' in st.session_state:
            if st.button("Perform AI QA Analysis"):
                with st.spinner("Analyzing the document..."):
                    qa_results = ai_qa_analysis(st.session_state['current_text'])
                st.subheader("AI QA Analysis Results:")
                st.write(qa_results)
        else:
            st.write("Please upload a valid document in the 'Document Upload & Translation' tab first.")

    with tab3:
        st.header("Property & Weather Report")
        if 'property_info' in st.session_state and 'weather_info' in st.session_state:
            report = create_property_report(st.session_state['property_info'], st.session_state['weather_info'])
            st.markdown(report)
            
            # Display location on a map if coordinates are available
            if isinstance(st.session_state['property_info'], dict) and 'latitude' in st.session_state['property_info'] and 'longitude' in st.session_state['property_info']:
                if (st.session_state['property_info']['latitude'] != 'N/A' and 
                    st.session_state['property_info']['longitude'] != 'N/A'):
                    st.subheader("Property Location")
                    st.map(data={"lat": [float(st.session_state['property_info']['latitude'])], 
                                 "lon": [float(st.session_state['property_info']['longitude'])]})
        else:
            st.write("Enter an address in the sidebar to get property and weather information.")

    # Automatically switch to the Property & Weather Report tab when info is fetched
    if 'active_tab' in st.session_state and st.session_state['active_tab'] == "Property & Weather Report":
        st.experimental_set_query_params(tab="Property & Weather Report")

if __name__ == "__main__":
    main()
