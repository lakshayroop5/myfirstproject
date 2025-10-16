from prefect import task
from agent_sdk import plan, Stage, get_logger, setup_logging
from pdf_parser_agent.vo.pdf_parser_vo import PdfParserVO

# Setup logging
setup_logging(level="INFO")
logger = get_logger(__name__)

@plan
@task(name="prepare_extraction_config")
def prepare_extraction_config(ctx) -> PdfParserVO:
    vo = ctx.data['input']
    strategy = vo.pick("plan", "parsing_strategy", "text")
    methods = vo.pick("plan", "extraction_methods", [])
    page_count = vo.pick("perceive", "page_count", 0)

    # Configure extraction parameters
    config = {
        "strategy": strategy,
        "methods": methods,
        "extract_text": "extract_text" in methods or "ocr_text" in methods,
        "extract_images": "extract_images" in methods,
        "extract_tables": "extract_tables" in methods,
        "extract_metadata": True,
        "page_range": (1, page_count),
        "ocr_settings": {
            "enabled": "ocr_text" in methods,
            "language": "eng",
            "dpi": 300,
        },
        "table_settings": {
            "detect_vertical": True,
            "detect_horizontal": True,
            "min_words": 3,
        },
    }

    vo.put("plan", extraction_config=config)

    return vo