from prefect import task
from agent_sdk import perceive, Stage, get_logger, setup_logging
from pdf_parser_agent.vo.pdf_parser_vo import PdfParserVO
from pdf_parser_agent.services.pdf_service import PDFService

# Setup logging
setup_logging(level="INFO")
logger = get_logger(__name__)

@perceive
@task(name="detect_pdf_type")
def detect_pdf_type(ctx) -> PdfParserVO:
    vo = ctx.data['input']
    file_path = vo.pick("perceive", "absolute_path", vo.file_path)
    characteristics = PDFService().detect_pdf_characteristics(file_path)

    vo.put("perceive",
           is_scanned=characteristics["is_scanned"],
           has_text=characteristics["has_text"],
           has_images=characteristics["has_images"],
           page_count=characteristics["page_count"],
           text_coverage=characteristics["text_coverage"],
           pdf_type="scanned" if characteristics["is_scanned"] else "native")

    return vo