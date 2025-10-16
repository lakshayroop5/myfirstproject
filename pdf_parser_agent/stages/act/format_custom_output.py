import json
from prefect import task
from agent_sdk import act, Stage, get_logger, setup_logging
from agent_sdk.tools.llm import OpenAITool
from pdf_parser_agent.vo.pdf_parser_vo import PdfParserVO

# Setup logging
setup_logging(level="INFO")
logger = get_logger(__name__)

@act
@task(name="format_custom_output")
def format_custom_output(ctx) -> PdfParserVO:
    """
    Format the output according to user's requirements.
    Only uses LLM if user has specified custom output format requirements.
    """
    vo = ctx.data['input']
    
    # Check if user wants custom output formatting
    if not vo.user_output_format:
        logger.info("No custom output format requested, skipping")
        vo.put("act", custom_format_applied=False)
        return vo
    
    logger.info(f"Applying custom output format: {vo.user_output_format}")
    
    # Get the extracted text
    extracted_text = vo.pick("act", "extracted_text", "")
    
    if not extracted_text:
        logger.warning("No extracted text available for formatting")
        vo.put("act", custom_format_applied=False, error="No text to format")
        return vo
    
    # Use LLM to format output according to user requirements
    formatted_output = _format_with_llm(extracted_text, vo.user_output_format, ctx)
    
    # Store formatted output in output_bundle
    current_bundle = vo.output_bundle or {}
    current_bundle["custom_formatted_output"] = formatted_output
    current_bundle["custom_format_request"] = vo.user_output_format
    vo.output_bundle = current_bundle
    
    vo.put("act", 
           custom_format_applied=True,
           formatted_output=formatted_output)
    
    logger.info("Custom output formatting completed")
    return vo


def _format_with_llm(text: str, format_requirement: str, ctx) -> str:
    """Use LLM to format the extracted text according to user requirements."""
    
    # Get LLM configuration from container if available
    llm_config = {}
    if hasattr(ctx.data['input'], 'container') and ctx.data['input'].container:
        llm_config = ctx.data['input'].container.get('llm_config', {})
    
    # Default config if not provided
    if not llm_config:
        llm_config = {
            'api_key': 'your-api-key-here',  # User should set this
            'model': 'gpt-4o-mini',  # Using efficient model
            'max_tokens': 1500,
            'temperature': 0.0  # Deterministic output
        }
    
    system_prompt = """You are an expert at analyzing and formatting document content.

Given the extracted text from a document and the user's formatting requirements, you will:
1. Analyze the content carefully
2. Extract the relevant information based on user's request
3. Format the output in a clear, structured way

Rules:
- Be concise and accurate
- Only include information that is actually present in the text
- If requested information is not found, state that clearly
- Format output in a readable structure (use bullet points, sections, etc.)
- Do not make up or hallucinate information"""

    # Limit text size to avoid token limits (keep first 8000 chars as that's ~2000 tokens)
    text_sample = text[:8000] if len(text) > 8000 else text
    
    user_msg = f"""Format the following extracted text according to this requirement: "{format_requirement}"

Extracted Text:
{text_sample}

Format the output as requested above."""

    try:
        # Create LLM tool instance
        llm = OpenAITool(name="output_formatter", config=llm_config)
        
        # Execute LLM call - handle async properly
        import asyncio
        try:
            # Try to get existing loop
            loop = asyncio.get_running_loop()
            # If we're in an async context, we need to use run_in_executor
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                result = executor.submit(
                    asyncio.run,
                    llm.execute(
                        prompt=user_msg,
                        system_prompt=system_prompt,
                        max_tokens=llm_config.get('max_tokens', 1500),
                        temperature=0.0
                    )
                ).result()
        except RuntimeError:
            # No event loop running, safe to use asyncio.run
            result = asyncio.run(
                llm.execute(
                    prompt=user_msg,
                    system_prompt=system_prompt,
                    max_tokens=llm_config.get('max_tokens', 1500),
                    temperature=0.0
                )
            )
        
        if result.status.value == "success":
            response_text = result.data.get("response", "")
            logger.info("Successfully formatted output with LLM")
            return response_text
        else:
            logger.warning(f"LLM formatting failed: {result.error}")
            return f"Error: Could not format output. {result.error}"
            
    except Exception as e:
        logger.error(f"Error using LLM for output formatting: {e}")
        return f"Error: Could not format output. {str(e)}"
