from typing import Dict, Any
from prefect import task
from agent_sdk import act, Stage, get_logger, setup_logging

# Setup logging
setup_logging(level="INFO")
logger = get_logger(__name__)

@act
@task(name="structure_output")
async def structure_output(ctx) -> Dict[str, Any]:
    context = ctx['input']
    act_data = context.get('stage_data', {}).get('act', {})
    plan_data = context.get('stage_data', {}).get('plan', {})
    perceive_data = context.get('stage_data', {}).get('perceive', {})
    
    # Retrieve extracted content
    text = act_data.get('extracted_text', '')
    images = act_data.get('extracted_images', [])
    tables = act_data.get('extracted_tables', [])
    metadata = act_data.get('extracted_metadata', {})

    # Update the parsed content
    context['parsed_content'] = {
        'text': text,
        'images': images,
        'tables': tables,
        'metadata': metadata
    }

    # Build output bundle
    context['output_bundle'] = {
        "file_path": context.get('file_path', ''),
        "session_id": context.get('session_id', ''),
        "parsing_strategy": plan_data.get('parsing_strategy', 'unknown'),
        "pdf_type": perceive_data.get('pdf_type', 'unknown'),
        "page_count": perceive_data.get('page_count', 0),
        "parsed_content": {
            "text": text,
            "text_length": len(text),
            "images": images,
            "image_count": len(images),
            "tables": tables,
            "table_count": len(tables),
            "metadata": metadata,
        },
        "extraction_config": plan_data.get('extraction_config', {}),
    }

    return {'input': context}