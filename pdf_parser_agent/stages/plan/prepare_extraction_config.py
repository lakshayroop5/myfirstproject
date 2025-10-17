from typing import Dict, Any
from prefect import task
from agent_sdk import plan, Stage, get_logger, setup_logging

# Setup logging
setup_logging(level="INFO")
logger = get_logger(__name__)

@plan
@task(name="prepare_extraction_config")
async def prepare_extraction_config(ctx) -> Dict[str, Any]:
    context = ctx['input']
    plan_data = context.get('stage_data', {}).get('plan', {})
    perceive_data = context.get('stage_data', {}).get('perceive', {})
    
    strategy = plan_data.get('parsing_strategy', 'text')
    methods = plan_data.get('extraction_methods', [])
    page_count = perceive_data.get('page_count', 0)

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

    # Initialize stage_data if needed
    if 'stage_data' not in context:
        context['stage_data'] = {}
    if 'plan' not in context['stage_data']:
        context['stage_data']['plan'] = {}
    
    context['stage_data']['plan']['extraction_config'] = config

    return {'input': context}