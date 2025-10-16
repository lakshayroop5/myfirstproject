import json
from prefect import task
from agent_sdk import act, Stage, get_logger, setup_logging
from agent_sdk.tools.hooks import ToolContext
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
    # Create ToolContext to access registered tools
    tools = ToolContext()
    formatted_output = _format_with_llm(extracted_text, vo.user_output_format, tools)
    
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


def _format_with_llm(text: str, format_requirement: str, tools) -> str:
    """Use LLM to format the extracted text according to user requirements."""
    
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
        # Check if OpenAI tool is available
        available_llm_tools = tools.get_available_tools(category='llm')
        if 'openai' not in available_llm_tools:
            logger.warning("OpenAI tool not available in registry")
            return "Error: OpenAI tool not configured. Please provide llm_config when initializing the agent."
        
        logger.info("Using OpenAI tool from registry")
        
        # Execute LLM call using the tool registry
        result = tools.execute_sync(
            'openai',
            prompt=user_msg,
            system_prompt=system_prompt,
            max_tokens=1500,
            temperature=0.0
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
