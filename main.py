import streamlit as st
import os
import PyPDF2
import openai

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

# Streamlit app
def main():
    st.title("PDF Translator and Analyzer App")

    # File upload
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

    if uploaded_file is not None:
        # Process the PDF
        text = extract_text_from_pdf(uploaded_file)
        
        # Save the text to a file
        filename = f"{uploaded_file.name.split('.')[0]}.txt"
        save_text_to_file(text, filename)
        st.success(f"File processed and saved as {filename} in the 'reports' folder")

        # Language selection
        languages = [
            "Spanish", "Chinese (Mandarin)", "Tagalog", "Vietnamese",
            "Arabic", "French", "Korean", "German"
        ]
        target_language = st.selectbox(
            "Select target language for translation",
            languages
        )

        # Translation button
        if st.button("Translate"):
            with st.spinner("Translating..."):
                translated_text = translate_text(text, target_language)
            st.subheader(f"Translated Text ({target_language}):")
            st.text_area("", translated_text, height=300)

        # AI QA Analysis button
        if st.button("Perform AI QA Analysis"):
            with st.spinner("Analyzing the document..."):
                qa_results = ai_qa_analysis(text)
            st.subheader("AI QA Analysis Results:")
            st.write(qa_results)

if __name__ == "__main__":
    main()
