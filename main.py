import streamlit as st
import os
import PyPDF2
import openai
import requests
from datetime import datetime
import io

# Set up OpenAI API key using Streamlit secrets
openai.api_key = st.secrets["OPENAI_API_KEY"]

# Function to extract text from PDF and save as txt
def extract_and_save_text_from_pdf(file):
    try:
        # Read the file content
        file_content = file.read()
        
        # Create a BytesIO object
        pdf_file = io.BytesIO(file_content)
        
        # Create PDF reader object
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        
        # Create Reports folder if it doesn't exist
        os.makedirs("Reports", exist_ok=True)
        
        # Save text to file
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
    return file.getvalue().decode("utf-8")

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
    # (The rest of the function remains the same as in the previous version)
    ...

# Streamlit app
def main():
    st.title("Document Processor and Info Gatherer App")

    # Sidebar for address input
    st.sidebar.header("Property Information")
    address = st.sidebar.text_input("Enter an address (U.S. only for weather data):")
    if st.sidebar.button("Get Info"):
        property_info, weather_info = gather_info(address)
        st.session_state['property_info'] = property_info
        st.session_state['weather_info'] = weather_info

    # Main area with tabs
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
