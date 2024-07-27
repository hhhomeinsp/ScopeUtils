import streamlit as st
import http.client
import json
import urllib.parse

# Initialize API keys
api_keys = {}
missing_keys = []
for key in ["RAPIDAPI_KEY"]:
    try:
        api_keys[key] = st.secrets[key]
    except KeyError:
        missing_keys.append(key)
        st.warning(f"Missing API key: {key}. Some features may be disabled.")

@st.cache_data
def get_property_info_from_rapidapi(street, city, state, zip_code, rapidapi_key):
    if not rapidapi_key:
        return {"error": "RapidAPI key is missing. Property information is unavailable."}

    host = "realty-mole-property-api.p.rapidapi.com"
    headers = {
        'x-rapidapi-key': rapidapi_key,
        'x-rapidapi-host': host
    }

    # Ensure correct address format: "Street, City, State Zip"
    address = f"{street.strip()}, {city.strip()}, {state.strip()} {zip_code.strip()}"
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

        # Extract and return relevant information
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
            rapidapi_key = api_keys.get("RAPIDAPI_KEY")
            if not rapidapi_key:
                st.error("RapidAPI key is missing. Cannot fetch property information.")
            else:
                with st.spinner("Fetching property information..."):
                    property_info = get_property_info_from_rapidapi(street, city, state, zip_code, rapidapi_key)
                
                if "error" in property_info:
                    st.error(property_info["error"])
                else:
                    st.success("Property information retrieved successfully!")
                    st.subheader("Property Details")
                    for key, value in property_info.items():
                        st.write(f"{key.replace('_', ' ').title()}: {value}")
                    
                    # Display location on a map if coordinates are available
                    if property_info['latitude'] != 'N/A' and property_info['longitude'] != 'N/A':
                        st.subheader("Property Location")
                        st.map(data={"lat": [float(property_info['latitude'])], "lon": [float(property_info['longitude'])]})
        else:
            st.warning("Please fill in all address fields.")

if __name__ == "__main__":
    main()
