from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from docx import Document
from openpyxl import load_workbook


class DocumentServiceError(Exception):
    pass


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".xlsx"}


def extract_document(filename: str, file_bytes: bytes) -> dict:
    extension = Path(filename).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise DocumentServiceError(
            "Supported formats are PDF, DOCX, TXT and XLSX."
        )

    if extension == ".pdf":
        return extract_pdf(file_bytes)

    if extension == ".docx":
        return extract_docx(file_bytes)

    if extension == ".txt":
        return extract_txt(file_bytes)

    if extension == ".xlsx":
        return extract_xlsx(file_bytes)

    raise DocumentServiceError("Unable to process this document.")


def extract_pdf(file_bytes: bytes) -> dict:
    try:
        reader = PdfReader(BytesIO(file_bytes))
        pages = []

        for number, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            pages.append(f"[Page {number}]\n{page_text}")

        return {
            "document_type": "PDF",
            "page_count": len(reader.pages),
            "text": "\n\n".join(pages),
        }

    except Exception as exc:
        raise DocumentServiceError(
            f"Could not read PDF: {exc}"
        ) from exc


def extract_docx(file_bytes: bytes) -> dict:
    try:
        document = Document(BytesIO(file_bytes))
        sections = []

        for paragraph in document.paragraphs:
            if paragraph.text.strip():
                sections.append(paragraph.text)

        for number, table in enumerate(document.tables, start=1):
            sections.append(f"\n[Table {number}]")

            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                sections.append(" | ".join(cells))

        return {
            "document_type": "DOCX",
            "page_count": None,
            "text": "\n".join(sections),
        }

    except Exception as exc:
        raise DocumentServiceError(
            f"Could not read Word document: {exc}"
        ) from exc


def extract_txt(file_bytes: bytes) -> dict:
    try:
        try:
            text = file_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = file_bytes.decode("cp1252")

        return {
            "document_type": "TXT",
            "page_count": None,
            "text": text,
        }

    except Exception as exc:
        raise DocumentServiceError(
            f"Could not read text document: {exc}"
        ) from exc


def extract_xlsx(file_bytes: bytes) -> dict:
    try:
        workbook = load_workbook(
            BytesIO(file_bytes),
            read_only=True,
            data_only=True,
        )

        sheet_names = workbook.sheetnames
        sections = []

        for sheet in workbook.worksheets:
            sections.append(f"\n[Sheet: {sheet.title}]")

            for row in sheet.iter_rows(values_only=True):
                values = [
                    str(value) if value is not None else ""
                    for value in row
                ]

                if any(values):
                    sections.append(" | ".join(values))

        workbook.close()

        return {
            "document_type": "XLSX",
            "page_count": None,
            "sheet_names": sheet_names,
            "text": "\n".join(sections),
        }

    except Exception as exc:
        raise DocumentServiceError(
            f"Could not read Excel: {exc}"
        ) from exc
