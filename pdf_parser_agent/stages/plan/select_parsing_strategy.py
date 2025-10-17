from typing import Dict, Any
from prefect import task
from agent_sdk import plan, Stage, get_logger, setup_logging

# Setup logging
setup_logging(level="INFO")
logger = get_logger(__name__)

@plan
@task(name="select_parsing_strategy")
async def select_parsing_strategy(ctx) -> Dict[str, Any]:
    context = ctx['input']
    perceive_data = context.get('stage_data', {}).get('perceive', {})
    is_scanned = perceive_data.get('is_scanned', False)
    has_text = perceive_data.get('has_text', False)
    has_images = perceive_data.get('has_images', False)
    text_coverage = perceive_data.get('text_coverage', 0.0)

    # Check if user has specified a preference for extraction strategy
    user_strategy = context.get('user_extraction_strategy')
    
    if user_strategy:
        # User has specified a preference, use it if valid
        logger.info(f"User requested extraction strategy: {user_strategy}")
        strategy = _map_user_strategy(user_strategy)
        methods = _get_methods_for_strategy(strategy)
        logger.info(f"Using user-preferred strategy: {strategy}")
    else:
        # Determine parsing strategy automatically based on PDF characteristics
        if is_scanned or text_coverage < 0.3:
            strategy = "ocr"
            methods = ["ocr_text", "extract_images"]
        elif has_text and has_images:
            strategy = "hybrid"
            methods = ["extract_text", "extract_images", "extract_tables"]
        elif has_text:
            strategy = "text"
            methods = ["extract_text", "extract_tables"]
        else:
            strategy = "images"
            methods = ["extract_images"]
        logger.info(f"Auto-selected strategy based on PDF type: {strategy}")

    # Initialize stage_data if needed
    if 'stage_data' not in context:
        context['stage_data'] = {}
    if 'plan' not in context['stage_data']:
        context['stage_data']['plan'] = {}
    
    context['stage_data']['plan'].update({
        'parsing_strategy': strategy,
        'extraction_methods': methods,
        'requires_ocr': (is_scanned or strategy == "ocr"),
        'user_overridden': (user_strategy is not None)
    })

    return {'input': context}


def _map_user_strategy(user_strategy: str) -> str:
    """Map user's natural language strategy to internal strategy names."""
    user_strategy_lower = user_strategy.lower()
    
    if "ocr" in user_strategy_lower or "scan" in user_strategy_lower:
        return "ocr"
    elif "text" in user_strategy_lower:
        return "text"
    elif "hybrid" in user_strategy_lower or "both" in user_strategy_lower:
        return "hybrid"
    elif "image" in user_strategy_lower:
        return "images"
    else:
        # Default to text if unclear
        return "text"


def _get_methods_for_strategy(strategy: str) -> list:
    """Get extraction methods for a given strategy."""
    strategy_methods = {
        "ocr": ["ocr_text", "extract_images"],
        "text": ["extract_text", "extract_tables"],
        "hybrid": ["extract_text", "extract_images", "extract_tables"],
        "images": ["extract_images"]
    }
    return strategy_methods.get(strategy, ["extract_text"])