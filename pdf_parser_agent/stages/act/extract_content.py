from prefect import task
from agent_sdk import act, Stage, get_logger, setup_logging
from pdf_parser_agent.vo.pdf_parser_vo import PdfParserVO
from pdf_parser_agent.services.pdf_service import PDFService

# Setup logging
setup_logging(level="INFO")
logger = get_logger(__name__)

@act
@task(name="extract_content")
def extract_content(ctx) -> PdfParserVO:
    vo = ctx.data['input']
    file_path = vo.pick("perceive", "absolute_path", vo.file_path)
    config = vo.pick("plan", "extraction_config", {})
    _pdf_service = PDFService()

    extracted_text = ""
    extracted_images = []
    extracted_tables = []
    extracted_metadata = {}

    # Extract text
    if config.get("extract_text", False):
        try:
            extracted_text = _pdf_service.extract_text(file_path)
        except Exception as e:
            vo.put("act", text_error=str(e))

    # Extract images
    if config.get("extract_images", False):
        try:
            extracted_images = _pdf_service.extract_images(file_path)
        except Exception as e:
            vo.put("act", images_error=str(e))

    # Extract tables
    if config.get("extract_tables", False):
        try:
            extracted_tables = _pdf_service.extract_tables(file_path)
        except Exception as e:
            vo.put("act", tables_error=str(e))

    # Extract metadata
    if config.get("extract_metadata", False):
        try:
            extracted_metadata = _pdf_service.extract_metadata(file_path)
        except Exception as e:
            vo.put("act", metadata_error=str(e))

    vo.put("act",
           extracted_text=extracted_text,
           extracted_images=extracted_images,
           extracted_tables=extracted_tables,
           extracted_metadata=extracted_metadata)

    return vo