import streamlit as st
import requests
from urllib.parse import quote

@st.cache_data
def get_property_info_from_rentcast(street, city, state, zip_code):
    if "RENTCAST_API_KEY" not in api_keys:
        return {"error": "Rentcast API key is missing. Property information is unavailable."}

    api_key = api_keys["RENTCAST_API_KEY"]
    
    # Format the address similarly to the web application URL
    address = f"{street}, {city}, {state}, {zip_code}"
    encoded_address = quote(address)
    
    url = f"https://api.rentcast.io/v1/properties"
    
    params = {
        "address": encoded_address,
        "type": "single-family"  # Adding this parameter based on the URL you provided
    }
    
    headers = {
        "Accept": "application/json",
        "X-Api-Key": api_key
    }

    st.write(f"Requesting data from Rentcast API for address: {address}")
    st.write(f"Request URL: {url}")
    st.write(f"Request Parameters: {params}")
    st.write(f"Request Headers: {headers}")
    
    try:
        response = requests.get(url, params=params, headers=headers)
        st.write(f"Response status code: {response.status_code}")
        st.write(f"Response headers: {response.headers}")
        st.write(f"Response content: {response.text[:500]}...")  # Truncate long responses

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
            else:
                return {"error": "No properties found for the given address"}
        elif response.status_code == 400:
            return {"error": f"Bad request: {response.text}"}
        elif response.status_code == 401:
            return {"error": "Authentication failed. Please check your Rentcast API key."}
        elif response.status_code == 404:
            return {"error": "Property not found in Rentcast database."}
        else:
            response.raise_for_status()

    except requests.exceptions.RequestException as e:
        st.error(f"Error making request to Rentcast API: {str(e)}")
        return {"error": f"Failed to retrieve property information: {str(e)}"}
    except Exception as e:
        st.error(f"Unexpected error in get_property_info_from_rentcast: {str(e)}")
        return {"error": f"An unexpected error occurred: {str(e)}"}

def main():
    st.title("Property Information Lookup")

    street = st.text_input("Street Address:")
    city = st.text_input("City:")
    state = st.text_input("State:")
    zip_code = st.text_input("ZIP Code:")

    if st.button("Get Property Info"):
        if street and city and state and zip_code:
            with st.spinner("Fetching property information..."):
                property_info = get_property_info_from_rentcast(street, city, state, zip_code)
            
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
