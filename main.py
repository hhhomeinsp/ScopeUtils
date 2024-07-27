import streamlit as st
import os
import PyPDF2
import openai
import requests
from datetime import datetime

# Set up OpenAI API key using Streamlit secrets
openai.api_key = st.secrets["OPENAI_API_KEY"]

# Function to extract text from PDF
def extract_text_from_pdf(file):
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

# Function to save text to file
def save_text_to_file(text, filename):
    os.makedirs("reports", exist_ok=True)
    with open(os.path.join("reports", filename), "w", encoding="utf-8") as f:
        f.write(text)

# Function to translate text
def translate_text(text, target_language):
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": f"You are a translator. Translate the following text to {target_language}."},
            {"role": "user", "content": text}
        ]
    )
    return response.choices[0].message.content

# Function for AI QA analysis
def ai_qa_analysis(text):
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an AI assistant tasked with analyzing a report. Provide a brief summary and key insights from the text."},
            {"role": "user", "content": f"Please analyze the following text and provide a summary and key insights:\n\n{text}"}
        ]
    )
    return response.choices[0].message.content

# Function to gather property and weather information
def gather_info(address):
    # Use OpenCage Geocoding API
    geocode_url = f"https://api.opencagedata.com/geocode/v1/json?q={address}&key={st.secrets['OPENCAGE_API_KEY']}"
    geocode_response = requests.get(geocode_url)
    geocode_data = geocode_response.json()
    
    if geocode_data['results']:
        lat = geocode_data['results'][0]['geometry']['lat']
        lon = geocode_data['results'][0]['geometry']['lng']
        
        # Get OpenStreetMap data
        osm_url = f"https://www.openstreetmap.org/api/0.6/map?bbox={lon-0.001},{lat-0.001},{lon+0.001},{lat+0.001}"
        osm_response = requests.get(osm_url)
        
        # Use OpenAI to interpret OSM data and estimate property information
        property_info = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an AI assistant tasked with estimating property information based on location and OpenStreetMap data."},
                {"role": "user", "content": f"Based on the address '{address}' and the following OpenStreetMap data, estimate the square footage, year built, and number of stories for the property. If you can't determine exact information, provide reasonable estimates based on the location and surrounding area. OpenStreetMap data: {osm_response.text[:1000]}"}
            ]
        ).choices[0].message.content

        # Get weather data from National Weather Service API
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
        return "Location not found", "Weather data unavailable"

# Streamlit app
def main():
    st.title("PDF Translator and Info Gatherer App")

    # Sidebar for address input
    st.sidebar.header("Property Information")
    address = st.sidebar.text_input("Enter an address (U.S. only for weather data):")
    if st.sidebar.button("Get Info"):
        property_info, weather_info = gather_info(address)
        st.session_state['property_info'] = property_info
        st.session_state['weather_info'] = weather_info

    # Main area with tabs
    tab1, tab2, tab3, tab4 = st.tabs(["PDF Upload & Translation", "AI QA Analysis", "Property Info", "Weather Info"])

    with tab1:
        st.header("PDF Upload & Translation")
        uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

        if uploaded_file is not None:
            text = extract_text_from_pdf(uploaded_file)
            filename = f"{uploaded_file.name.split('.')[0]}.txt"
            save_text_to_file(text, filename)
            st.success(f"File processed and saved as {filename} in the 'reports' folder")

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
        if uploaded_file is not None:
            if st.button("Perform AI QA Analysis"):
                with st.spinner("Analyzing the document..."):
                    qa_results = ai_qa_analysis(text)
                st.subheader("AI QA Analysis Results:")
                st.write(qa_results)
        else:
            st.write("Please upload a PDF file in the 'PDF Upload & Translation' tab first.")

    with tab3:
        st.header("Property Information")
        if 'property_info' in st.session_state:
            st.write(st.session_state['property_info'])
        else:
            st.write("Enter an address in the sidebar to get property information.")

    with tab4:
        st.header("Weather Information")
        if 'weather_info' in st.session_state:
            st.write(st.session_state['weather_info'])
        else:
            st.write("Enter an address in the sidebar to get weather information.")

if __name__ == "__main__":
    main()
