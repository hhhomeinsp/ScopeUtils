import streamlit as st
import requests
from urllib.parse import quote

# Initialize API keys
api_keys = {}
missing_keys = []
for key in ["OPENAI_API_KEY", "OPENCAGE_API_KEY", "RENTCAST_API_KEY"]:
    try:
        api_keys[key] = st.secrets[key]
    except KeyError:
        missing_keys.append(key)
        st.warning(f"Missing API key: {key}. Some features may be disabled.")

def geocode_address(address, api_key):
    url = f"https://api.opencagedata.com/geocode/v1/json?q={quote(address)}&key={api_key}"
    response = requests.get(url)
    data = response.json()
    if data['results']:
        location = data['results'][0]['geometry']
        return f"{location['lat']},{location['lng']}"
    return None

@st.cache_data
def get_property_info_from_rentcast(street, city, state, zip_code, rentcast_api_key):
    if not rentcast_api_key:
        return {"error": "Rentcast API key is missing. Property information is unavailable."}

    base_url = "https://api.rentcast.io/v1/properties"
    headers = {
        "Accept": "application/json",
        "X-Api-Key": rentcast_api_key
    }

    # Ensure correct address format: "Street, City, State Zip"
    address = f"{street.strip()}, {city.strip()}, {state.strip()} {zip_code.strip()}"
    encoded_address = quote(address)
    url = f"{base_url}?address={encoded_address}"

    # Debugging information
    st.write(f"Encoded address: {encoded_address}")
    st.write(f"Request URL: {url}")
    st.write(f"Request Headers: {headers}")

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        response_data = response.json()

        if response_data.get('properties'):
            property_info = response_data['properties'][0]
        else:
            return {"error": "No property information found for the given location."}

        # Extract and return relevant information
        return {
            "address": property_info.get('formattedAddress', 'N/A'),
            "property_type": property_info.get('propertyType', 'N/A'),
            "bedrooms": property_info.get('bedrooms', 'N/A'),
            "bathrooms": property_info.get('bathrooms', 'N/A'),
            "square_footage": property_info.get('squareFootage', 'N/A'),
            "lot_size": property_info.get('lotSize', 'N/A'),
            "year_built": property_info.get('yearBuilt', 'N/A'),
            "last_sale_date": property_info.get('lastSaleDate', 'N/A'),
            "last_sale_price": property_info.get('lastSalePrice', 'N/A'),
            "zoning": property_info.get('zoning', 'N/A'),
            "features": property_info.get('features', {}),
            "owner_occupied": property_info.get('ownerOccupied', 'N/A'),
            "latitude": property_info.get('latitude', 'N/A'),
            "longitude": property_info.get('longitude', 'N/A')
        }

    except requests.exceptions.RequestException as e:
        st.error(f"Failed to retrieve property information: {str(e)}")
        return {"error": f"Failed to retrieve property information: {str(e)}"}

def main():
    st.title("Property Information Lookup")

    if missing_keys:
        st.error("One or more API keys are missing. Please check the API keys and try again.")
        return

    with st.form(key='property_form'):
        street = st.text_input("Street Address:", key="street_input")
        city = st.text_input("City:", key="city_input")
        state = st.text_input("State:", key="state_input")
        zip_code = st.text_input("ZIP Code:", key="zip_input")
        submit_button = st.form_submit_button(label='Get Property Info')

    if submit_button:
        if street and city and state and zip_code:
            rentcast_api_key = api_keys.get("RENTCAST_API_KEY")
            if not rentcast_api_key:
                st.error("Rentcast API key is missing. Cannot fetch property information.")
            else:
                with st.spinner("Fetching property information..."):
                    property_info = get_property_info_from_rentcast(street, city, state, zip_code, rentcast_api_key)

                if "error" in property_info:
                    st.error(property_info["error"])
                else:
                    st.success("Property information retrieved successfully!")
                    st.subheader("Property Details")
                    for key, value in property_info.items():
                        if key != "features":
                            st.write(f"{key.replace('_', ' ').title()}: {value}")

                    if property_info["features"]:
                        st.subheader("Property Features")
                        for key, value in property_info["features"].items():
                            st.write(f"{key.replace('_', ' ').title()}: {value}")

                    # Display location on a map if coordinates are available
                    if property_info['latitude'] != 'N/A' and property_info['longitude'] != 'N/A':
                        st.subheader("Property Location")
                        st.map(data={"lat": [float(property_info['latitude'])], "lon": [float(property_info['longitude'])]})
        else:
            st.warning("Please fill in all address fields.")

if __name__ == "__main__":
    main()
