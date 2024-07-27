import streamlit as st
import requests
from urllib.parse import quote
import os
import pdfplumber
import openai
from datetime import datetime
import io
import chardet

# Initialize a dictionary to store available API keys
api_keys = {}

# Try to get each API key, storing them if available
for key in ["OPENAI_API_KEY", "OPENCAGE_API_KEY", "RENTCAST_API_KEY"]:
    try:
        api_keys[key] = st.secrets[key]
    except KeyError:
        st.warning(f"Missing API key: {key}. Some features may be disabled.")

# Check if we have the minimum required keys to run the app
if not all(key in api_keys for key in ["OPENAI_API_KEY", "OPENCAGE_API_KEY"]):
    st.error("Critical API keys are missing. The app cannot function properly.")
    st.stop()

# Set OpenAI API key
openai.api_key = api_keys.get("OPENAI_API_KEY")

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

def translate_text(text, target_language):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": f"You are a language translator. Translate the following text to {target_language}."},
            {"role": "user", "content": text}
        ]
    )
    return response.choices[0].message.content

def ai_qa_analysis(text):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are an expert analyst able to QA home inspection reports and provide feedback on any errors such as grammatical, spelling, contradictions, or possible oversights. Your goal is to improve the quality, accuracy, and readability of the home inspection report to improve the quality of the report and reduce liability."},
            {"role": "user", "content": f"Please analyze the following text and provide a summary of any errors:\n\n{text}"}
        ]
    )
    return response.choices[0].message.content

def geocode_address(address):
    if "OPENCAGE_API_KEY" not in api_keys:
        st.error("OpenCage API key is not set in Streamlit secrets.")
        return None

    api_key = api_keys["OPENCAGE_API_KEY"]
    url = f"https://api.opencagedata.com/geocode/v1/json?q={quote(address)}&key={api_key}"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data['results']:
            result = data['results'][0]
            return f"{result['geometry']['lat']},{result['geometry']['lng']}"
    except Exception as e:
        st.error(f"Error geocoding address: {str(e)}")
    return None

@st.cache_data
def get_property_info_from_rentcast(street, city, state, zip_code):
    if "RENTCAST_API_KEY" not in api_keys:
        return {"error": "Rentcast API key is missing. Property information is unavailable."}

    api_key = api_keys["RENTCAST_API_KEY"]
    
    address_formats = [
        f"{street}, {city}, {state}, {zip_code}",
        f"{street.replace('Hwy', 'Highway')}, {city}, {state}, {zip_code}",
        f"{street}, {city}, {state} {zip_code}",
        f"{street.replace('Hwy', 'Highway')}, {city}, {state} {zip_code}",
        f"{street.replace('Highway', 'Hwy')}, {city}, {state}, {zip_code}",
        f"{street.replace('Highway', 'Hwy')}, {city}, {state} {zip_code}",
        f"{street.split(',')[0]}, {city}, {state}, {zip_code}"
    ]
    
    for address in address_formats:
        encoded_address = quote(address)
        url = f"https://api.rentcast.io/v1/properties?address={encoded_address}"
        
        headers = {
            "Accept": "application/json",
            "X-Api-Key": api_key
        }

        st.write(f"Trying address format: {address}")
        st.write(f"Request URL: {url}")
        
        try:
            response = requests.get(url, headers=headers)
            st.write(f"Response status code: {response.status_code}")
            st.write(f"Response content: {response.text[:500]}...")

            if response.status_code == 200:
                data = response.json()
                if data.get('properties'):
                    property_info = data['properties'][0]
                    return {
                        "square_footage": property_info.get('squareFootage', 'N/A'),
                        "year_built": property_info.get('yearBuilt', 'N/A'),
                        "bedrooms": property_info.get('bedrooms', 'N/A'),
                        "bathrooms": property_info.get('bathrooms', 'N/A'),
                        "property_type": property_info.get('propertyType', 'N/A'),
                        "last_sale_date": property_info.get('lastSaleDate', 'N/A'),
                        "last_sale_price": property_info.get('lastSalePrice', 'N/A'),
                        "lot_size": property_info.get('lotSize', 'N/A'),
                        "zoning": property_info.get('zoning', 'N/A'),
                        "features": property_info.get('features', {}),
                        "owner_occupied": property_info.get('ownerOccupied', 'N/A')
                    }
            elif response.status_code == 400:
                st.warning(f"Address format '{address}' not recognized. Trying next format...")
            else:
                response.raise_for_status()

        except requests.exceptions.RequestException as e:
            st.error(f"Error making request to Rentcast API: {str(e)}")
    
    st.warning("All address formats failed. Attempting to geocode the address...")
    geocoded = geocode_address(f"{street}, {city}, {state}, {zip_code}")
    if geocoded:
        url = f"https://api.rentcast.io/v1/properties?address={geocoded}"
        st.write(f"Trying geocoded coordinates: {geocoded}")
        st.write(f"Request URL: {url}")
        try:
            response = requests.get(url, headers=headers)
            st.write(f"Response status code: {response.status_code}")
            st.write(f"Response content: {response.text[:500]}...")
            if response.status_code == 200:
                data = response.json()
                if data.get('properties'):
                    property_info = data['properties'][0]
                    return {
                        "square_footage": property_info.get('squareFootage', 'N/A'),
                        "year_built": property_info.get('yearBuilt', 'N/A'),
                        "bedrooms": property_info.get('bedrooms', 'N/A'),
                        "bathrooms": property_info.get('bathrooms', 'N/A'),
                        "property_type": property_info.get('propertyType', 'N/A'),
                        "last_sale_date": property_info.get('lastSaleDate', 'N/A'),
                        "last_sale_price": property_info.get('lastSalePrice', 'N/A'),
                        "lot_size": property_info.get('lotSize', 'N/A'),
                        "zoning": property_info.get('zoning', 'N/A'),
                        "features": property_info.get('features', {}),
                        "owner_occupied": property_info.get('ownerOccupied', 'N/A')
                    }
        except requests.exceptions.RequestException as e:
            st.error(f"Error making request to Rentcast API with geocoded coordinates: {str(e)}")
    
    return {"error": "Failed to retrieve property information for all attempted address formats and geocoding."}

def get_property_info_fallback(street, city, state, zip_code):
    geocoded = geocode_address(f"{street}, {city}, {state}, {zip_code}")
    
    if geocoded:
        lat, lon = geocoded.split(',')
        
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            address = data.get('address', {})
            
            return {
                "error": "Rentcast data unavailable. Showing basic location info.",
                "latitude": lat,
                "longitude": lon,
                "city": address.get('city', city),
                "state": address.get('state', state),
                "country": address.get('country', 'USA'),
                "postcode": address.get('postcode', zip_code)
            }
        except Exception as e:
            st.error(f"Error fetching location info: {str(e)}")
    
    return {
        "error": "Unable to retrieve property information. Please enter details manually.",
        "latitude": "N/A",
        "longitude": "N/A",
        "city": city,
        "state": state,
        "country": "USA",
        "postcode": zip_code
    }

def get_property_info(street, city, state, zip_code):
    rentcast_info = get_property_info_from_rentcast(street, city, state, zip_code)
    
    if "error" in rentcast_info:
        st.warning("Rentcast data unavailable. Fetching basic location info...")
        return get_property_info_fallback(street, city, state, zip_code)
    
    return rentcast_info

def main():
    st.title("Document Processor and Info Gatherer App")

    st.sidebar.header("Property Information")
    street = st.sidebar.text_input("Street Address:")
    city = st.sidebar.text_input("City:")
    state = st.sidebar.text_input("State (2-letter code):")
    zip_code = st.sidebar.text_input("ZIP Code:")

    if st.sidebar.button("Get Property Info"):
        if street and city and state and zip_code:
            with st.spinner("Fetching property information..."):
                property_info = get_property_info(street, city, state, zip_code)
            st.session_state['property_info'] = property_info
        else:
            st.sidebar.warning("Please fill in all address fields.")

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
                st.write(f"Property Type: {st.session_state['property_info'].get('property_type', 'N/A')}")
                st.write(f"Square Footage: {st.session_state['property_info'].get('square_footage', 'N/A')}")
                st.write(f"Year Built: {st.session_state['property_info'].get('year_built', 'N/A')}")
                st.write(f"Bedrooms: {st.session_state['property_info'].get('bedrooms', 'N/A')}")
                st.write(f"Bathrooms: {st.session_state['property_info'].get('bathrooms', 'N/A')}")
                st.write(f"Lot Size: {st.session_state['property_info'].get('lot_size', 'N/A')} sq ft")
                st.write(f"Zoning: {st.session_state['property_info'].get('zoning', 'N/A')}")
                st.write(f"Last Sale Date: {st.session_state['property_info'].get('last_sale_date', 'N/A')}")
                st.write(f"Last Sale Price: ${st.session_state['property_info'].get('last_sale_price', 'N/A')}")
                st.write(f"Owner Occupied: {'Yes' if st.session_state['property_info'].get('owner_occupied') else 'No'}")
                
                if 'features' in st.session_state['property_info']:
                    st.subheader("Property Features")
                    features = st.session_state['property_info']['features']
                    for key, value in features.items():
                        st.write(f"{key.replace('Type', '').title()}: {value}")
        else:
            st.write("Enter an address in the sidebar to get property information.")

    with tab4:
        st.header("Weather Information")
        if 'weather_info' in st.session_state:
            if isinstance(st.session_state['weather_info'], dict) and 'error' in st.session_state['weather_info']:
                st.error(st.session_state['weather_info']['error'])
            else:
                st.write(st.session_state['weather_info'])
        else:
            st.write("Enter an address in the sidebar to get weather information.")

if __name__ == "__main__":
    main()
