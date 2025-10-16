from prefect import task
from agent_sdk import act, Stage, get_logger, setup_logging
from pdf_parser_agent.vo.pdf_parser_vo import PdfParserVO

# Setup logging
setup_logging(level="INFO")
logger = get_logger(__name__)

@act
@task(name="structure_output")
def structure_output(ctx) -> PdfParserVO:
    vo = ctx.data['input']
    # Retrieve extracted content
    text = vo.pick("act", "extracted_text", "")
    images = vo.pick("act", "extracted_images", [])
    tables = vo.pick("act", "extracted_tables", [])
    metadata = vo.pick("act", "extracted_metadata", {})

    # Update the parsed content
    vo.update_parsed_content(
        text=text,
        images=images,
        tables=tables,
        metadata=metadata
    )

    # Build output bundle
    vo.output_bundle = {
        "file_path": vo.file_path,
        "session_id": vo.session_id,
        "parsing_strategy": vo.pick("plan", "parsing_strategy", "unknown"),
        "pdf_type": vo.pick("perceive", "pdf_type", "unknown"),
        "page_count": vo.pick("perceive", "page_count", 0),
        "parsed_content": {
            "text": text,
            "text_length": len(text),
            "images": images,
            "image_count": len(images),
            "tables": tables,
            "table_count": len(tables),
            "metadata": metadata,
        },
        "extraction_config": vo.pick("plan", "extraction_config", {}),
    }

    return vo