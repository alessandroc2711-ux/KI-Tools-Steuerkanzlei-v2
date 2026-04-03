"""
TAXPILOT AI – KI ASSISTENT FÜR STEUERKANZLEIEN
LIVE AI VERSION MIT .ENV SUPPORT
Mit vollständiger Selbstbedienungs-Oberfläche und erklärtem Prompt
"""

import fitz
import json
import os
from dotenv import load_dotenv
from docx import Document
import streamlit as st
from pdf2image import convert_from_bytes
import pytesseract
from openai import OpenAI

# ======================================
# LOAD ENV
# ======================================
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")

if not API_KEY:
    raise ValueError("OPENAI_API_KEY nicht gefunden. Bitte .env prüfen.")

client = OpenAI(api_key=API_KEY)

# ======================================
# CONFIG
# ======================================
DICT_FILE = "dictionary.json"

DEFAULT_DICT = {
    "Alessandro Codazzi": "MitarbeiterX",
    "Firma AG": "FirmaY",
    "München": "OrtX",
    "15. März 2026": "DatumX"
}

# ======================================
# STREAMLIT CONFIG
# ======================================
st.set_page_config(
    page_title="TaxPilot AI",
    layout="wide"
)

st.title("TaxPilot AI – KI Assistent für Steuerkanzleien")

st.markdown("""
Willkommen bei **TaxPilot AI**.

Dieses Tool ermöglicht eine **vollständig selbstbedienbare Nutzung**:

- Upload und Anonymisierung von PDF- und Word-Dokumenten  
- Bearbeitbares, manuelles Wörterbuch  
- KI-gestützte steuerrechtliche Analyse  
- Sofort einsetzbar für Kanzlei-Demos  

Alle Schritte werden direkt in der Oberfläche erklärt.
""")

# ======================================
# DICTIONARY
# ======================================
def load_dictionary():
    if os.path.exists(DICT_FILE):
        with open(DICT_FILE, "r", encoding="utf-8") as f:
            dictionary = json.load(f)
    else:
        dictionary = DEFAULT_DICT.copy()

    return dict(sorted(dictionary.items()))


def save_dictionary(dictionary):
    sorted_dict = dict(sorted(dictionary.items()))

    with open(DICT_FILE, "w", encoding="utf-8") as f:
        json.dump(
            sorted_dict,
            f,
            indent=4,
            ensure_ascii=False
        )

# ======================================
# ANONYMIZATION
# ======================================
def anonymize_text(text, dictionary):
    result = text

    for original, replacement in dictionary.items():
        result = result.replace(original, replacement)

    return result

# ======================================
# FILE EXTRACTION
# ======================================
def extract_pdf_text(file_pdf):
    file_pdf.seek(0)

    pdf = fitz.open(
        stream=file_pdf.read(),
        filetype="pdf"
    )

    text = ""

    for page in pdf:
        text += page.get_text()

    if text.strip():
        return text

    return extract_ocr_text(file_pdf)


def extract_word_text(file_docx):
    file_docx.seek(0)

    doc = Document(file_docx)

    text = ""

    for para in doc.paragraphs:
        text += para.text + "\n"

    return text


def extract_ocr_text(file_pdf):
    file_pdf.seek(0)

    images = convert_from_bytes(file_pdf.read())

    text = ""

    for img in images:
        text += pytesseract.image_to_string(
            img,
            lang="deu"
        ) + "\n"

    return text

# ======================================
# WORD EXPORT
# ======================================
def create_word(text, filename="document_anon.docx"):
    doc = Document()

    for line in text.split("\n"):
        doc.add_paragraph(line)

    doc.save(filename)

    return filename

# ======================================
# PROMPT ENGINEERING
# ======================================
def build_tax_prompt(case_text):
    prompt = f"""
Du bist ein Senior-Steuerberater einer führenden deutschen Steuerkanzzlei.

Erstelle eine belastbare steuerrechtliche Fachanalyse.

Mandantenfall:
{case_text}

Bitte strukturiert beantworten:

1. Executive Summary
2. Steuerrechtliche Fragestellung
3. Anwendbare Normen (mit Paragraphen)
4. Relevante BFH / FG Urteile
5. Expertenkommentare
6. Risikoanalyse (niedrig / mittel / hoch)
7. Konkrete Handlungsempfehlung
8. Empfohlene nächste Schritte für die Kanzlei

Bitte juristisch präzise, mandantenorientiert und praxisnah.

Antwort ausschließlich auf Deutsch.
"""
    return prompt

# ======================================
# OPENAI CALL
# ======================================
def run_ai_analysis(prompt):
    response = client.responses.create(
        model="gpt-4.1",
        input=prompt
    )
    return response.output_text

# ======================================
# SESSION STATE
# ======================================
if "dictionary" not in st.session_state:
    st.session_state.dictionary = load_dictionary()

if "original_text" not in st.session_state:
    st.session_state.original_text = ""

if "anonymized_text" not in st.session_state:
    st.session_state.anonymized_text = ""

# ======================================
# SIDEBAR
# ======================================
st.sidebar.header("Anonymisierungs-Wörterbuch")

st.sidebar.markdown("""
Format: `Original = Ersatz`

Beispiel:  
`BMW AG = FirmaX`
""")

dictionary_text = "\n".join(
    [
        f"{k} = {v}"
        for k, v in sorted(
            st.session_state.dictionary.items()
        )
    ]
)

edited_dictionary_text = st.sidebar.text_area(
    "Wörterbuch bearbeiten",
    value=dictionary_text,
    height=300
)

if st.sidebar.button("Wörterbuch speichern"):
    new_dict = {}

    for line in edited_dictionary_text.split("\n"):
        if "=" in line:
            key, value = line.split("=", 1)
            new_dict[key.strip()] = value.strip()

    st.session_state.dictionary = dict(
        sorted(new_dict.items())
    )

    save_dictionary(
        st.session_state.dictionary
    )

    if st.session_state.original_text:
        st.session_state.anonymized_text = anonymize_text(
            st.session_state.original_text,
            st.session_state.dictionary
        )

    st.sidebar.success(
        "Wörterbuch gespeichert und Text aktualisiert"
    )

# ======================================
# STEP 1
# ======================================
st.header("1. Dokument Upload")

uploaded_file = st.file_uploader(
    "PDF oder Word auswählen",
    type=["pdf", "docx"]
)

if uploaded_file is not None:
    if st.button("Dokument verarbeiten"):

        if uploaded_file.name.endswith(".pdf"):
            text = extract_pdf_text(uploaded_file)
        else:
            text = extract_word_text(uploaded_file)

        st.session_state.original_text = text
        st.session_state.anonymized_text = anonymize_text(
            text,
            st.session_state.dictionary
        )

# ======================================
# STEP 2
# ======================================
if st.session_state.original_text:
    st.subheader("Originaltext")

    st.text_area(
        "Original",
        st.session_state.original_text,
        height=200
    )

if st.session_state.anonymized_text:
    st.subheader("Anonymisierter Text")

    st.session_state.anonymized_text = st.text_area(
        "Bearbeitbarer Text",
        st.session_state.anonymized_text,
        height=300
    )

    if st.button("Text erneut anonymisieren"):
        st.session_state.anonymized_text = anonymize_text(
            st.session_state.original_text,
            st.session_state.dictionary
        )

        st.success("Text aktualisiert")

    filename = create_word(
        st.session_state.anonymized_text
    )

    with open(filename, "rb") as f:
        st.download_button(
            "Word herunterladen",
            data=f,
            file_name=filename
        )

# ======================================
# STEP 3 AI ANALYSIS
# ======================================
if st.session_state.anonymized_text:
    st.header("2. KI Steueranalyse")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Anonymisierung", "Aktiv")

    with col2:
        st.metric("KI Analyse", "Bereit")

    with col3:
        st.metric("Kanzlei Demo", "Live")

    st.info(
        "Die KI erstellt eine vollständige steuerliche Auswertung des anonymisierten Falls."
    )

    if st.button("KI Analyse starten"):
        with st.spinner("KI analysiert den Fall..."):
            prompt = build_tax_prompt(
                st.session_state.anonymized_text
            )

            result = run_ai_analysis(prompt)

        st.success("Analyse abgeschlossen")

        st.subheader("Analyseergebnis")
        st.markdown(result)

        with st.expander("Verwendeter Prompt – Erklärung"):
            st.markdown("""
**Was ist ein Prompt?**  
Ein Prompt ist die professionelle Fachanweisung an die KI.

**Warum ist das relevant?**
- vollständige Nachvollziehbarkeit
- auditierbare Arbeitsweise
- konsistente Qualitätsstandards

**Prompt-Inhalt:**
""")

            st.code(prompt)"""
TAXPILOT AI – KI ASSISTENT FÜR STEUERKANZLEIEN
LIVE AI VERSION MIT .ENV SUPPORT
Mit vollständiger Selbstbedienungs-Oberfläche und erklärtem Prompt
"""

import fitz
import json
import os
from dotenv import load_dotenv
from docx import Document
import streamlit as st
from pdf2image import convert_from_bytes
import pytesseract
from openai import OpenAI

# ======================================
# LOAD ENV
# ======================================
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")

if not API_KEY:
    raise ValueError("OPENAI_API_KEY nicht gefunden. Bitte .env prüfen.")

client = OpenAI(api_key=API_KEY)

# ======================================
# CONFIG
# ======================================
DICT_FILE = "dictionary.json"

DEFAULT_DICT = {
    "Alessandro Codazzi": "MitarbeiterX",
    "Firma AG": "FirmaY",
    "München": "OrtX",
    "15. März 2026": "DatumX"
}

# ======================================
# STREAMLIT CONFIG
# ======================================
st.set_page_config(
    page_title="TaxPilot AI",
    layout="wide"
)

st.title("TaxPilot AI – KI Assistent für Steuerkanzleien")

st.markdown("""
Willkommen bei **TaxPilot AI**.

Dieses Tool ermöglicht eine **vollständig selbstbedienbare Nutzung**:

- Upload und Anonymisierung von PDF- und Word-Dokumenten  
- Bearbeitbares, manuelles Wörterbuch  
- KI-gestützte steuerrechtliche Analyse  
- Sofort einsetzbar für Kanzlei-Demos  

Alle Schritte werden direkt in der Oberfläche erklärt.
""")

# ======================================
# DICTIONARY
# ======================================
def load_dictionary():
    if os.path.exists(DICT_FILE):
        with open(DICT_FILE, "r", encoding="utf-8") as f:
            dictionary = json.load(f)
    else:
        dictionary = DEFAULT_DICT.copy()

    return dict(sorted(dictionary.items()))


def save_dictionary(dictionary):
    sorted_dict = dict(sorted(dictionary.items()))

    with open(DICT_FILE, "w", encoding="utf-8") as f:
        json.dump(
            sorted_dict,
            f,
            indent=4,
            ensure_ascii=False
        )

# ======================================
# ANONYMIZATION
# ======================================
def anonymize_text(text, dictionary):
    result = text

    for original, replacement in dictionary.items():
        result = result.replace(original, replacement)

    return result

# ======================================
# FILE EXTRACTION
# ======================================
def extract_pdf_text(file_pdf):
    file_pdf.seek(0)

    pdf = fitz.open(
        stream=file_pdf.read(),
        filetype="pdf"
    )

    text = ""

    for page in pdf:
        text += page.get_text()

    if text.strip():
        return text

    return extract_ocr_text(file_pdf)


def extract_word_text(file_docx):
    file_docx.seek(0)

    doc = Document(file_docx)

    text = ""

    for para in doc.paragraphs:
        text += para.text + "\n"

    return text


def extract_ocr_text(file_pdf):
    file_pdf.seek(0)

    images = convert_from_bytes(file_pdf.read())

    text = ""

    for img in images:
        text += pytesseract.image_to_string(
            img,
            lang="deu"
        ) + "\n"

    return text

# ======================================
# WORD EXPORT
# ======================================
def create_word(text, filename="document_anon.docx"):
    doc = Document()

    for line in text.split("\n"):
        doc.add_paragraph(line)

    doc.save(filename)

    return filename

# ======================================
# PROMPT ENGINEERING
# ======================================
def build_tax_prompt(case_text):
    prompt = f"""
Du bist ein Senior-Steuerberater einer führenden deutschen Steuerkanzzlei.

Erstelle eine belastbare steuerrechtliche Fachanalyse.

Mandantenfall:
{case_text}

Bitte strukturiert beantworten:

1. Executive Summary
2. Steuerrechtliche Fragestellung
3. Anwendbare Normen (mit Paragraphen)
4. Relevante BFH / FG Urteile
5. Expertenkommentare
6. Risikoanalyse (niedrig / mittel / hoch)
7. Konkrete Handlungsempfehlung
8. Empfohlene nächste Schritte für die Kanzlei

Bitte juristisch präzise, mandantenorientiert und praxisnah.

Antwort ausschließlich auf Deutsch.
"""
    return prompt

# ======================================
# OPENAI CALL
# ======================================
def run_ai_analysis(prompt):
    response = client.responses.create(
        model="gpt-4.1",
        input=prompt
    )
    return response.output_text

# ======================================
# SESSION STATE
# ======================================
if "dictionary" not in st.session_state:
    st.session_state.dictionary = load_dictionary()

if "original_text" not in st.session_state:
    st.session_state.original_text = ""

if "anonymized_text" not in st.session_state:
    st.session_state.anonymized_text = ""

# ======================================
# SIDEBAR
# ======================================
st.sidebar.header("Anonymisierungs-Wörterbuch")

st.sidebar.markdown("""
Format: `Original = Ersatz`

Beispiel:  
`BMW AG = FirmaX`
""")

dictionary_text = "\n".join(
    [
        f"{k} = {v}"
        for k, v in sorted(
            st.session_state.dictionary.items()
        )
    ]
)

edited_dictionary_text = st.sidebar.text_area(
    "Wörterbuch bearbeiten",
    value=dictionary_text,
    height=300
)

if st.sidebar.button("Wörterbuch speichern"):
    new_dict = {}

    for line in edited_dictionary_text.split("\n"):
        if "=" in line:
            key, value = line.split("=", 1)
            new_dict[key.strip()] = value.strip()

    st.session_state.dictionary = dict(
        sorted(new_dict.items())
    )

    save_dictionary(
        st.session_state.dictionary
    )

    if st.session_state.original_text:
        st.session_state.anonymized_text = anonymize_text(
            st.session_state.original_text,
            st.session_state.dictionary
        )

    st.sidebar.success(
        "Wörterbuch gespeichert und Text aktualisiert"
    )

# ======================================
# STEP 1
# ======================================
st.header("1. Dokument Upload")

uploaded_file = st.file_uploader(
    "PDF oder Word auswählen",
    type=["pdf", "docx"]
)

if uploaded_file is not None:
    if st.button("Dokument verarbeiten"):

        if uploaded_file.name.endswith(".pdf"):
            text = extract_pdf_text(uploaded_file)
        else:
            text = extract_word_text(uploaded_file)

        st.session_state.original_text = text
        st.session_state.anonymized_text = anonymize_text(
            text,
            st.session_state.dictionary
        )

# ======================================
# STEP 2
# ======================================
if st.session_state.original_text:
    st.subheader("Originaltext")

    st.text_area(
        "Original",
        st.session_state.original_text,
        height=200
    )

if st.session_state.anonymized_text:
    st.subheader("Anonymisierter Text")

    st.session_state.anonymized_text = st.text_area(
        "Bearbeitbarer Text",
        st.session_state.anonymized_text,
        height=300
    )

    if st.button("Text erneut anonymisieren"):
        st.session_state.anonymized_text = anonymize_text(
            st.session_state.original_text,
            st.session_state.dictionary
        )

        st.success("Text aktualisiert")

    filename = create_word(
        st.session_state.anonymized_text
    )

    with open(filename, "rb") as f:
        st.download_button(
            "Word herunterladen",
            data=f,
            file_name=filename
        )

# ======================================
# STEP 3 AI ANALYSIS
# ======================================
if st.session_state.anonymized_text:
    st.header("2. KI Steueranalyse")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Anonymisierung", "Aktiv")

    with col2:
        st.metric("KI Analyse", "Bereit")

    with col3:
        st.metric("Kanzlei Demo", "Live")

    st.info(
        "Die KI erstellt eine vollständige steuerliche Auswertung des anonymisierten Falls."
    )

    if st.button("KI Analyse starten"):
        with st.spinner("KI analysiert den Fall..."):
            prompt = build_tax_prompt(
                st.session_state.anonymized_text
            )

            result = run_ai_analysis(prompt)

        st.success("Analyse abgeschlossen")

        st.subheader("Executive Summary")
        st.info(
            "Automatisch generierte Fachanalyse für Mandantenfall"
        )

        st.subheader("Analyseergebnis")
        st.write(result)

        with st.expander("Verwendeter Prompt – Erklärung"):
            st.markdown("""
**Was ist ein Prompt?**  
Ein Prompt ist die professionelle Fachanweisung an die KI.

**Warum ist das relevant?**
- vollständige Nachvollziehbarkeit
- auditierbare Arbeitsweise
- konsistente Qualitätsstandards

**Prompt-Inhalt:**
""")

            st.code(prompt)
