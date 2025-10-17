from typing import Dict, Any
from prefect import task
from agent_sdk import act, Stage, get_logger, setup_logging
from pdf_parser_agent.services.pdf_service import PDFService

# Setup logging
setup_logging(level="INFO")
logger = get_logger(__name__)

@act
@task(name="extract_content")
async def extract_content(ctx) -> Dict[str, Any]:
    context = ctx['input']
    perceive_data = context.get('stage_data', {}).get('perceive', {})
    plan_data = context.get('stage_data', {}).get('plan', {})
    
    file_path = perceive_data.get('absolute_path', context.get('file_path', ''))
    config = plan_data.get('extraction_config', {})
    _pdf_service = PDFService()

    extracted_text = ""
    extracted_images = []
    extracted_tables = []
    extracted_metadata = {}

    # Initialize stage_data if needed
    if 'stage_data' not in context:
        context['stage_data'] = {}
    if 'act' not in context['stage_data']:
        context['stage_data']['act'] = {}
    
    # Extract text
    if config.get("extract_text", False):
        try:
            extracted_text = _pdf_service.extract_text(file_path)
        except Exception as e:
            context['stage_data']['act']['text_error'] = str(e)

    # Extract images
    if config.get("extract_images", False):
        try:
            extracted_images = _pdf_service.extract_images(file_path)
        except Exception as e:
            context['stage_data']['act']['images_error'] = str(e)

    # Extract tables
    if config.get("extract_tables", False):
        try:
            extracted_tables = _pdf_service.extract_tables(file_path)
        except Exception as e:
            context['stage_data']['act']['tables_error'] = str(e)

    # Extract metadata
    if config.get("extract_metadata", False):
        try:
            extracted_metadata = _pdf_service.extract_metadata(file_path)
        except Exception as e:
            context['stage_data']['act']['metadata_error'] = str(e)

    context['stage_data']['act'].update({
        'extracted_text': extracted_text,
        'extracted_images': extracted_images,
        'extracted_tables': extracted_tables,
        'extracted_metadata': extracted_metadata
    })

    return {'input': context}