import streamlit as st
import os
import pdfplumber
import openai
import requests
from datetime import datetime
import io
import chardet

try:
    # Temporarily print all available keys to debug
    st.write("Available keys in st.secrets:", list(st.secrets.keys()))
    
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    OPENCAGE_API_KEY = st.secrets["OPENCAGE_API_KEY"]
    RENTCAST_API_KEY = st.secrets["RENTCAST_API_KEY"]
except KeyError as e:
    st.error(f"Missing API key: {e}")
    st.stop()

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

# Function to get property information from RentCast API
@st.cache_data
def get_property_info_from_rentcast(address):
    try:
        url = f"https://api.rentcast.io/v1/properties?address={address}"
        headers = {
            "X-Api-Key": RENTCAST_API_KEY
        }

        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            st.write(f"Failed to retrieve property information: {response.status_code}")
            st.write(response.json())
            return {"error": "Failed to retrieve property information"}

        data = response.json()
        if not data['properties']:
            return {"error": "No properties found"}

        property_info = data['properties'][0]

        return {
            "square_footage": property_info.get('squareFootage', 'N/A'),
            "year_built": property_info.get('yearBuilt', 'N/A'),
            "stories": property_info.get('stories', 'N/A')
        }

    except Exception as e:
        return {"error": str(e)}

# Function to gather property and weather information
@st.cache_data
def gather_info(address):
    geocode_url = f"https://api.opencagedata.com/geocode/v1/json?q={address}&key={OPENCAGE_API_KEY}"
    geocode_response = requests.get(geocode_url)
    geocode_data = geocode_response.json()
    
    if geocode_data['results']:
        lat = geocode_data['results'][0]['geometry']['lat']
        lon = geocode_data['results'][0]['geometry']['lng']

        property_info = get_property_info_from_rentcast(address)

        weather_url = f"https://api.weather.gov/points/{lat},{lon}"
        weather_response = requests.get(weather_url)
        if weather_response.status_code == 200:
            weather_data = weather_response.json()
            forecast_url = weather_data['properties']['forecast']
            forecast_response = requests.get(forecast_url)
            if forecast_response.status_code == 200:
                forecast_data = forecast_response.json()
                current_period = forecast_data['properties']['periods'][0]
                
                weather_info = f"Temperature: {current_period['temperature']}°{current_period['temperatureUnit']}\n"
                weather_info += f"Conditions: {current_period['shortForecast']}\n"
                weather_info += f"Wind: {current_period['windSpeed']} {current_period['windDirection']}\n"
                weather_info += f"Forecast: {current_period['detailedForecast']}"
            else:
                weather_info = "Weather forecast data unavailable"
        else:
            weather_info = "Weather data unavailable"

        return property_info, weather_info
    else:
        return {"error": "Location not found"}, {"error": "Weather data unavailable"}

# Streamlit app
def main():
    st.title("Document Processor and Info Gatherer App")

    st.sidebar.header("Property Information")
    address = st.sidebar.text_input("Enter an address (U.S. only for weather data):")
    if st.sidebar.button("Get Info"):
        property_info, weather_info = gather_info(address)
        st.session_state['property_info'] = property_info
        st.session_state['weather_info'] = weather_info

    tab1, tab2, tab3, tab4 = st.tabs(["Document Upload & Translation", "AI QA Analysis", "Property Info", "Weather Info"])

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
        st.header("Property Information")
        if 'property_info' in st.session_state:
            if 'error' in st.session_state['property_info']:
                st.error(st.session_state['property_info']['error'])
            else:
                st.write(st.session_state['property_info'])
        else:
            st.write("Enter an address in the sidebar to get property information.")

    with tab4:
        st.header("Weather Information")
        if 'weather_info' in st.session_state:
            if 'error' in st.session_state['weather_info']:
                st.error(st.session_state['weather_info']['error'])
            else:
                st.write(st.session_state['weather_info'])
        else:
            st.write("Enter an address in the sidebar to get weather information.")

if __name__ == "__main__":
    main()
