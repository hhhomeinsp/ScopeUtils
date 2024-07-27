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
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except PyPDF2.errors.PdfReadError:
        st.error("Error: The uploaded PDF file appears to be corrupted or in an unsupported format.")
        return None

# Function to read text file
def read_text_file(file):
    return file.getvalue().decode("utf-8")

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
    # (The rest of the function remains the same as in the previous version)
    ...

# Streamlit app
def main():
    st.title("Document Translator and Info Gatherer App")

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
        file_type = st.radio("Select file type:", ("PDF", "Text"))
        
        if file_type == "PDF":
            uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
        else:
            uploaded_file = st.file_uploader("Choose a text file", type="txt")

        if uploaded_file is not None:
            if file_type == "PDF":
                text = extract_text_from_pdf(uploaded_file)
            else:
                text = read_text_file(uploaded_file)
            
            if text:
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
        if uploaded_file is not None and text:
            if st.button("Perform AI QA Analysis"):
                with st.spinner("Analyzing the document..."):
                    qa_results = ai_qa_analysis(text)
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
