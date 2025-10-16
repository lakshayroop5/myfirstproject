import os
from typing import Any, Dict, List, Optional
import PyPDF2
import pdfplumber
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import io

class PDFService:
    def extract_text(self, file_path: str) -> str:
        text = ""
        try:
            # Try pdfplumber first (better for complex layouts)
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            # Fallback to PyPDF2
            try:
                with open(file_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    for page in reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
            except Exception as inner_e:
                raise RuntimeError(f"Failed to extract text: {inner_e}")

        return text.strip()

    def extract_images(self, file_path: str) -> List[Dict[str, Any]]:
        images = []
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    if hasattr(page, 'images'):
                        for img_idx, img in enumerate(page.images):
                            images.append({
                                "page": page_num,
                                "index": img_idx,
                                "x0": img.get("x0"),
                                "y0": img.get("y0"),
                                "x1": img.get("x1"),
                                "y1": img.get("y1"),
                                "width": img.get("width"),
                                "height": img.get("height"),
                            })
        except Exception as e:
            raise RuntimeError(f"Failed to extract images: {e}")

        return images

    def extract_tables(self, file_path: str) -> List[Dict[str, Any]]:
        tables = []
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_tables = page.extract_tables()
                    if page_tables:
                        for table_idx, table_data in enumerate(page_tables):
                            tables.append({
                                "page": page_num,
                                "index": table_idx,
                                "rows": len(table_data),
                                "columns": len(table_data[0]) if table_data else 0,
                                "data": table_data,
                            })
        except Exception as e:
            raise RuntimeError(f"Failed to extract tables: {e}")

        return tables

    def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        metadata = {
            "file_path": file_path,
            "file_size": 0,
            "page_count": 0,
            "title": None,
            "author": None,
            "subject": None,
            "creator": None,
            "producer": None,
            "creation_date": None,
        }

        try:
            # Get file size
            metadata["file_size"] = os.path.getsize(file_path)

            # Extract PDF metadata
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                metadata["page_count"] = len(reader.pages)

                if reader.metadata:
                    metadata.update({
                        "title": reader.metadata.get("/Title"),
                        "author": reader.metadata.get("/Author"),
                        "subject": reader.metadata.get("/Subject"),
                        "creator": reader.metadata.get("/Creator"),
                        "producer": reader.metadata.get("/Producer"),
                        "creation_date": str(reader.metadata.get("/CreationDate")),
                    })
        except Exception as e:
            raise RuntimeError(f"Failed to extract metadata: {e}")

        return metadata

    def detect_pdf_characteristics(self, file_path: str) -> Dict[str, Any]:
        characteristics = {
            "is_scanned": False,
            "has_text": False,
            "has_images": False,
            "page_count": 0,
            "text_coverage": 0.0,
        }

        try:
            with pdfplumber.open(file_path) as pdf:
                characteristics["page_count"] = len(pdf.pages)

                text_pages = 0
                for page in pdf.pages:
                    text = page.extract_text()
                    if text and len(text.strip()) > 50:
                        text_pages += 1
                        characteristics["has_text"] = True

                    if hasattr(page, 'images') and len(page.images) > 0:
                        characteristics["has_images"] = True

                if characteristics["page_count"] > 0:
                    characteristics["text_coverage"] = text_pages / characteristics["page_count"]

                # If very low text coverage, likely scanned
                if characteristics["text_coverage"] < 0.3:
                    characteristics["is_scanned"] = True

        except Exception as e:
            raise RuntimeError(f"Failed to detect PDF characteristics: {e}")

        return characteristics