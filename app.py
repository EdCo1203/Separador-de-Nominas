import streamlit as st
import io
import re
import zipfile
import unicodedata
from typing import Optional
from pypdf import PdfReader, PdfWriter


def limpiar_para_archivo(s: str) -> str:
    s = s.strip().upper()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^A-Z0-9 _-]", "", s)
    s = re.sub(r"\s+", " ", s)
    s = s.replace(" ", "_")
    return s or "SIN_NOMBRE"


def extraer_nombre(texto: str) -> Optional[str]:
    patron = r"TRABAJADOR/A.*?\n\s*([A-ZÁÉÍÓÚÑ ]{5,})\s+PERSONAL"
    m = re.search(patron, texto, re.DOTALL)
    if m:
        return m.group(1).strip()
    return None


def extraer_periodo(texto: str) -> str:
    patron = r"MENS\s+(\d{1,2})\s+([A-ZÁÉÍÓÚ]{3})\s+(\d{2})\s+a"
    m = re.search(patron, texto)
    if not m:
        return "0000-00"

    mes_txt, anio = m.group(2), m.group(3)

    meses = {
        "ENE": "01", "FEB": "02", "MAR": "03", "ABR": "04",
        "MAY": "05", "JUN": "06", "JUL": "07", "AGO": "08",
        "SEP": "09", "OCT": "10", "NOV": "11", "DIC": "12"
    }

    return f"20{anio}-{meses.get(mes_txt, '00')}"


# --- Streamlit APP ---
st.title("📄 Separador de Nóminas PDF – Entregalia Tools")
uploaded_file = st.file_uploader("Sube el PDF con las nóminas", type=["pdf"])

if uploaded_file:
    pdf_reader = PdfReader(uploaded_file)
    total_pages = len(pdf_reader.pages)

    st.info(f"📑 El PDF tiene {total_pages} páginas.")

    if st.button("Generar PDFs individuales"):
        progress = st.progress(0)
        status = st.empty()

        primer_texto = (pdf_reader.pages[0].extract_text() or "")
        periodo_zip = extraer_periodo(primer_texto)
        carpeta_zip = f"nominas_{periodo_zip}"

        zip_buffer = io.BytesIO()
        usados = {}

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            for i, page in enumerate(pdf_reader.pages):
                status.text(f"Procesando página {i+1} de {total_pages}…")

                texto = page.extract_text() or ""
                nombre = extraer_nombre(texto) or f"Pagina_{i+1}"
                nombre_limpio = limpiar_para_archivo(nombre)
                periodo = extraer_periodo(texto)

                # Nombre final: NOMBRE_TRABAJADOR_2026-03.pdf
                nombre_base = f"{nombre_limpio}_{periodo}"

                count = usados.get(nombre_base, 0) + 1
                usados[nombre_base] = count
                sufijo = f"_{count}" if count > 1 else ""

                filename = f"{carpeta_zip}/{nombre_base}{sufijo}.pdf"

                writer = PdfWriter()
                writer.add_page(page)

                pdf_bytes = io.BytesIO()
                writer.write(pdf_bytes)
                pdf_bytes.seek(0)

                zipf.writestr(filename, pdf_bytes.read())
                progress.progress((i + 1) / total_pages)

        zip_buffer.seek(0)
        st.success("✔ Proceso finalizado.")
        st.download_button(
            label="⬇️ Descargar ZIP con nóminas separadas",
            data=zip_buffer,
            file_name=f"{carpeta_zip}.zip",
            mime="application/zip"
        )