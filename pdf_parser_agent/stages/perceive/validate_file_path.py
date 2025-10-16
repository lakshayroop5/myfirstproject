import os
from prefect import task
from agent_sdk import perceive, Stage, get_logger, setup_logging
from pdf_parser_agent.vo.pdf_parser_vo import PdfParserVO

# Setup logging
setup_logging(level="INFO")
logger = get_logger(__name__)

@perceive
@task(name="validate_file_path")
def validate_file_path(ctx) -> PdfParserVO:
    vo = ctx.data['input']
    file_path = vo.file_path

    # Check if file exists
    if not os.path.exists(file_path):
        vo.put("perceive", 
               file_valid=False, 
               error=f"File not found: {file_path}")
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    # Check if it's a file (not directory)
    if not os.path.isfile(file_path):
        vo.put("perceive", 
               file_valid=False, 
               error=f"Path is not a file: {file_path}")
        raise ValueError(f"Path is not a file: {file_path}")

    # Check if file is readable
    if not os.access(file_path, os.R_OK):
        vo.put("perceive", 
               file_valid=False, 
               error=f"File is not readable: {file_path}")
        raise PermissionError(f"Cannot read file: {file_path}")

    # Check file extension
    _, ext = os.path.splitext(file_path)
    if ext.lower() != '.pdf':
        vo.put("perceive", 
               file_valid=False, 
               error=f"File is not a PDF: {file_path}")
        raise ValueError(f"File must have .pdf extension: {file_path}")

    # Get file size
    file_size = os.path.getsize(file_path)

    vo.put("perceive", 
           file_valid=True,
           file_size=file_size,
           absolute_path=os.path.abspath(file_path))

    return vo