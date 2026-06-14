import fitz


def load_pdf_from_stream(uploaded_file):
    """Ładuje tekst ze strumienia pamięci Streamlit (obiekt UploadedFile)."""
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    text = "".join(page.get_text() for page in doc)
    doc.close()
    return text
