import streamlit as st
import os
import PyPDF2
import openai
import requests
from geopy.geocoders import Nominatim
from bs4 import BeautifulSoup

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
        model="gpt-4",
        messages=[
            {"role": "system", "content": f"You are a translator. Translate the following text to {target_language}."},
            {"role": "user", "content": text}
        ]
    )
    return response.choices[0].message.content

# Function for AI QA analysis
def ai_qa_analysis(text):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are an AI assistant tasked with analyzing a report. Provide a brief summary and key insights from the text."},
            {"role": "user", "content": f"Please analyze the following text and provide a summary and key insights:\n\n{text}"}
        ]
    )
    return response.choices[0].message.content

# Function to gather property and weather information
def gather_info(address):
    # Initialize geocoder
    geolocator = Nominatim(user_agent="myGeocoder")
    location = geolocator.geocode(address)
    
    if location:
        lat, lon = location.latitude, location.longitude
        
        # Use OpenAI to search for property information
        property_info = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an AI assistant tasked with finding property information."},
                {"role": "user", "content": f"Find the square footage, year built, and number of stories for the property at {address}. If you can't find exact information, provide estimates based on similar properties in the area."}
            ]
        ).choices[0].message.content

        # Get weather data
        weather_url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={st.secrets['OPENWEATHER_API_KEY']}&units=metric"
        weather_response = requests.get(weather_url)
        weather_data = weather_response.json()
        
        weather_info = f"Current temperature: {weather_data['main']['temp']}°C\n"
        weather_info += f"Weather conditions: {weather_data['weather'][0]['description']}\n"
        weather_info += f"Humidity: {weather_data['main']['humidity']}%\n"
        weather_info += f"Wind speed: {weather_data['wind']['speed']} m/s"

        return property_info, weather_info
    else:
        return "Location not found", "Weather data unavailable"

# Streamlit app
def main():
    st.title("PDF Translator and Info Gatherer App")

    # Sidebar for address input
    st.sidebar.header("Property Information")
    address = st.sidebar.text_input("Enter an address:")
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
