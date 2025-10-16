from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass(frozen=True)
class ParsedContent:
    text: str = ""
    images: List[Dict[str, Any]] = field(default_factory=list)
    tables: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PdfParserVO:
    session_id: str
    user_prompt: str = ""
    file_path: str = ""
    container: Any = None

    # User preferences extracted from prompt
    user_extraction_strategy: Optional[str] = None
    user_output_format: Optional[str] = None

    # stage scratchpads
    stage_data: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)

    # outputs
    parsed_content: ParsedContent = field(default_factory=ParsedContent)
    sources: List[Dict[str, Any]] = field(default_factory=list)
    output_bundle: Dict[str, Any] = field(default_factory=dict)

    def put(self, stage: str, **kv):
        self.stage_data.setdefault(stage, {}).update(kv)
        return self

    def pick(self, stage: str, key: str, default=None):
        return self.stage_data.get(stage, {}).get(key, default)

    def update_parsed_content(self, **kwargs):
        current = self.parsed_content
        new = ParsedContent(
            text=kwargs.get("text", current.text),
            images=kwargs.get("images", current.images),
            tables=kwargs.get("tables", current.tables),
            metadata=kwargs.get("metadata", current.metadata),
        )
        object.__setattr__(self, "parsed_content", new)
        return self