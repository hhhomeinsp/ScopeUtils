import streamlit as st
import requests
from urllib.parse import quote

# Initialize API keys
api_keys = {}
for key in ["OPENAI_API_KEY", "OPENCAGE_API_KEY", "RENTCAST_API_KEY"]:
    try:
        api_keys[key] = st.secrets[key]
    except KeyError:
        st.warning(f"Missing API key: {key}. Some features may be disabled.")

import streamlit as st
import requests
from urllib.parse import quote

def geocode_address(address, api_key):
    url = f"https://api.opencagedata.com/geocode/v1/json?q={quote(address)}&key={api_key}"
    response = requests.get(url)
    data = response.json()
    if data['results']:
        location = data['results'][0]['geometry']
        return f"{location['lat']},{location['lng']}"
    return None

@st.cache_data
def get_property_info_from_rentcast(street, city, state, zip_code, rentcast_api_key, opencage_api_key):
    if not rentcast_api_key:
        return {"error": "Rentcast API key is missing. Property information is unavailable."}

    address = f"{street}, {city}, {state}, {zip_code}"
    encoded_address = quote(address)
    
    url = "https://api.rentcast.io/v1/properties"
    
    # Try with encoded address
    params = {
        "address": encoded_address,
        "type": "single-family"
    }
    
    headers = {
        "Accept": "application/json",
        "X-Api-Key": rentcast_api_key
    }

    st.write(f"Requesting data from Rentcast API for encoded address: {encoded_address}")
    response = requests.get(url, params=params, headers=headers)
    
    if response.status_code != 200:
        # If encoded address fails, try with unencoded address
        params["address"] = address
        st.write(f"Retrying with unencoded address: {address}")
        response = requests.get(url, params=params, headers=headers)
    
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
    
    # If address lookup fails, try with geocoded coordinates
    st.write("Address lookup failed. Attempting to use geocoded coordinates.")
    geocoded = geocode_address(address, opencage_api_key)
    if geocoded:
        params["address"] = geocoded
        st.write(f"Requesting data from Rentcast API with coordinates: {geocoded}")
        response = requests.get(url, params=params, headers=headers)
        
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
    
    # If all attempts fail, return an error
    st.error(f"Failed to retrieve property information. Status code: {response.status_code}")
    st.error(f"Response content: {response.text}")
    return {"error": f"Failed to retrieve property information. Status code: {response.status_code}"}

def main():
    st.title("Property Information Lookup")

    street = st.text_input("Street Address:")
    city = st.text_input("City:")
    state = st.text_input("State:")
    zip_code = st.text_input("ZIP Code:")

    if st.button("Get Property Info"):
        if street and city and state and zip_code:
            rentcast_api_key = api_keys.get("RENTCAST_API_KEY")
            opencage_api_key = api_keys.get("OPENCAGE_API_KEY")
            if not rentcast_api_key or not opencage_api_key:
                st.error("Rentcast API key or OpenCage API key is missing. Cannot fetch property information.")
            else:
                with st.spinner("Fetching property information..."):
                    property_info = get_property_info_from_rentcast(street, city, state, zip_code, rentcast_api_key, opencage_api_key)
                
                if "error" in property_info:
                    st.error(property_info["error"])
                else:
                    st.success("Property information retrieved successfully!")
                    for key, value in property_info.items():
                        if key != "features":
                            st.write(f"{key.replace('_', ' ').title()}: {value}")
                    
                    if property_info["features"]:
                        st.subheader("Property Features")
                        for key, value in property_info["features"].items():
                            st.write(f"{key.replace('_', ' ').title()}: {value}")
        else:
            st.warning("Please fill in all address fields.")

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
