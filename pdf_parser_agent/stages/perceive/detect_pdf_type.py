from typing import Dict, Any
from prefect import task
from agent_sdk import perceive, Stage, get_logger, setup_logging
from pdf_parser_agent.services.pdf_service import PDFService

# Setup logging
setup_logging(level="INFO")
logger = get_logger(__name__)

@perceive
@task(name="detect_pdf_type")
async def detect_pdf_type(ctx) -> Dict[str, Any]:
    context = ctx['input']
    
    # Get file path
    file_path = context['stage_data'].get('perceive', {}).get('absolute_path', context.get('file_path', ''))
    characteristics = PDFService().detect_pdf_characteristics(file_path)

    # Initialize stage_data if needed
    if 'stage_data' not in context:
        context['stage_data'] = {}
    if 'perceive' not in context['stage_data']:
        context['stage_data']['perceive'] = {}
    
    context['stage_data']['perceive'].update({
        'is_scanned': characteristics["is_scanned"],
        'has_text': characteristics["has_text"],
        'has_images': characteristics["has_images"],
        'page_count': characteristics["page_count"],
        'text_coverage': characteristics["text_coverage"],
        'pdf_type': "scanned" if characteristics["is_scanned"] else "native"
    })

    return {'input': context}