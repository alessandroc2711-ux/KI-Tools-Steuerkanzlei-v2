"""
TAXPILOT AI – KI ASSISTENT FÜR STEUERKANZLEIEN
LIVE AI VERSION MIT .ENV SUPPORT
Mit vollständiger Selbstbedienungs-Oberfläche und erklärtem Prompt
"""

import os
import json
from dotenv import load_dotenv
import fitz
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
st.set_page_config(page_title="TaxPilot AI", layout="wide")
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
# DICTIONARY FUNCTIONS
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
        json.dump(sorted_dict, f, indent=4, ensure_ascii=False)

def anonymize_text(text, dictionary):
    for original, replacement in dictionary.items():
        text = text.replace(original, replacement)
    return text

# ======================================
# FILE EXTRACTION
# ======================================
def extract_pdf_text(file_pdf):
    file_pdf.seek(0)
    content = file_pdf.read()
    pdf = fitz.open(stream=content, filetype="pdf")
    text = "".join(page.get_text() for page in pdf)
    if text.strip():
        return text
    # OCR fallback
    images = convert_from_bytes(content)
    text = "\n".join(pytesseract.image_to_string(img, lang="deu") for img in images)
    return text

def extract_word_text(file_docx):
    file_docx.seek(0)
    doc = Document(file_docx)
    return "\n".join(para.text for para in doc.paragraphs)

# ======================================
# WORD EXPORT
# ======================================
def create_word(text, filename="document_anon.docx"):
    doc = Document()
    for line in text.split("\n"):
        doc.add_paragraph(line)
    doc.save(filename)
    return filename

def create_checklist_word(checklist_items, filename="checklist.docx"):
    doc = Document()
    doc.add_paragraph("TaxPilot AI – Aufgaben-Checkliste\n")
    for task, checked in checklist_items.items():
        symbol = "☑" if checked else "☐"
        doc.add_paragraph(f"{symbol} {task}")
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
    response = client.responses.create(model="gpt-4.1", input=prompt)
    return response.output_text

# ======================================
# CHECKLIST PARSING
# ======================================
def parse_checklist(result_text):
    checklist = {}
    if "Empfohlene nächste Schritte für die Kanzlei" in result_text:
        checklist_text = result_text.split("Empfohlene nächste Schritte für die Kanzlei")[-1]
        for line in checklist_text.split("\n"):
            line = line.strip()
            if line.startswith(("☐", "☑")):
                task = line.lstrip("☐☑ ").lstrip("* ").strip()
                if task and not task.lower() in ["**", "zusammenfassende position:"]:
                    checklist[task] = line.startswith("☑")
    return checklist

# ======================================
# SESSION STATE
# ======================================
if "dictionary" not in st.session_state:
    st.session_state.dictionary = load_dictionary()
if "original_text" not in st.session_state:
    st.session_state.original_text = ""
if "anonymized_text" not in st.session_state:
    st.session_state.anonymized_text = ""
if "checklist" not in st.session_state:
    st.session_state.checklist = {}

# ======================================
# SIDEBAR – Wörterbuch
# ======================================
st.sidebar.header("Anonymisierungs-Wörterbuch")
st.sidebar.markdown("Format: `Original = Ersatz`\n\nBeispiel:  `BMW AG = FirmaX`")
dictionary_text = "\n".join(f"{k} = {v}" for k, v in sorted(st.session_state.dictionary.items()))
edited_dictionary_text = st.sidebar.text_area("Wörterbuch bearbeiten", value=dictionary_text, height=300)

if st.sidebar.button("Wörterbuch speichern"):
    new_dict = {}
    for line in edited_dictionary_text.split("\n"):
        if "=" in line:
            key, value = line.split("=", 1)
            new_dict[key.strip()] = value.strip()
    st.session_state.dictionary = dict(sorted(new_dict.items()))
    save_dictionary(st.session_state.dictionary)
    if st.session_state.original_text:
        st.session_state.anonymized_text = anonymize_text(st.session_state.original_text, st.session_state.dictionary)
    st.sidebar.success("Wörterbuch gespeichert und Text aktualisiert")

# ======================================
# STEP 1 – FILE UPLOAD
# ======================================
st.header("1. Dokument Upload")
uploaded_file = st.file_uploader("PDF oder Word auswählen", type=["pdf", "docx"])
if uploaded_file is not None and st.button("Dokument verarbeiten"):
    if uploaded_file.name.endswith(".pdf"):
        text = extract_pdf_text(uploaded_file)
    else:
        text = extract_word_text(uploaded_file)
    st.session_state.original_text = text
    st.session_state.anonymized_text = anonymize_text(text, st.session_state.dictionary)

# ======================================
# STEP 2 – TEXT ANZEIGE & BEARBEITUNG
# ======================================
if st.session_state.original_text:
    st.subheader("Originaltext")
    st.text_area("Original", st.session_state.original_text, height=200)

if st.session_state.anonymized_text:
    st.subheader("Anonymisierter Text")
    st.session_state.anonymized_text = st.text_area("Bearbeitbarer Text", st.session_state.anonymized_text, height=300)
    if st.button("Text erneut anonymisieren"):
        st.session_state.anonymized_text = anonymize_text(st.session_state.original_text, st.session_state.dictionary)
        st.success("Text aktualisiert")
    filename = create_word(st.session_state.anonymized_text)
    with open(filename, "rb") as f:
        st.download_button("Word herunterladen", data=f, file_name=filename)

# ======================================
# STEP 3 – AI ANALYSIS
# ======================================
if st.session_state.anonymized_text:
    st.header("2. KI Steueranalyse")
    st.info("Die KI erstellt eine vollständige steuerliche Auswertung des anonymisierten Falls.")
    if st.button("KI Analyse starten"):
        with st.spinner("KI analysiert den Fall..."):
            prompt = build_tax_prompt(st.session_state.anonymized_text)
            result = run_ai_analysis(prompt)
        st.success("Analyse abgeschlossen")
        st.subheader("Analyseergebnis")
        st.markdown(result)

        # Extrahiere Checklist
        st.session_state.checklist.update(parse_checklist(result))

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

# ======================================
# STEP 4 – DYNAMISCHE CHECKLIST
# ======================================
st.header("3. Aufgaben-Checkliste")
st.markdown("Aktivieren Sie die Tasks, die erledigt sind:")
for task in list(st.session_state.checklist.keys()):
    st.session_state.checklist[task] = st.checkbox(task, value=st.session_state.checklist[task])

if st.button("Checkliste als Word herunterladen"):
    checklist_file = create_checklist_word(st.session_state.checklist)
    with open(checklist_file, "rb") as f:
        st.download_button("Download Checklist", data=f, file_name=checklist_file)
