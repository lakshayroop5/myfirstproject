from typing import Any, Dict, Optional
import json

class LLMService:

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.cfg = config or {}
        self._client = None

    async def setup(self):
        self._client = True

    async def close(self):
        self._client = None

    async def analyze_content_structure(self, text: str) -> Dict[str, Any]:
        if not self._client:
            await self.setup()

        analysis = {
            "has_headings": "heading" in text.lower() or "#" in text,
            "has_lists": any(marker in text for marker in ["•", "-", "1.", "2."]),
            "has_tables": "table" in text.lower(),
            "estimated_sections": len(text.split("\n\n")),
            "language": "en",
            "document_type": self._infer_document_type(text),
        }

        return analysis

    def _infer_document_type(self, text: str) -> str:
        text_lower = text.lower()

        if "invoice" in text_lower or "bill" in text_lower:
            return "invoice"
        elif "contract" in text_lower or "agreement" in text_lower:
            return "contract"
        elif "resume" in text_lower or "curriculum vitae" in text_lower:
            return "resume"
        elif "report" in text_lower:
            return "report"
        else:
            return 'general'