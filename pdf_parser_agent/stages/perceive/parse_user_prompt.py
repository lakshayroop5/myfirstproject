import json
from prefect import task
from agent_sdk import perceive, Stage, get_logger, setup_logging
from agent_sdk.tools.hooks import ToolContext
from pdf_parser_agent.vo.pdf_parser_vo import PdfParserVO

# Setup logging
setup_logging(level="INFO")
logger = get_logger(__name__)

@perceive
@task(name="parse_user_prompt")
def parse_user_prompt(ctx) -> PdfParserVO:
    """
    Parse the user's natural language prompt using LLM to extract:
    - File path (required)
    - Extraction strategy preference (optional)
    - Output format requirements (optional)
    
    Always uses LLM for intelligent parsing.
    """
    vo = ctx.data['input']
    user_prompt = vo.user_prompt
    
    if not user_prompt:
        raise ValueError("user_prompt is required")
    
    # Always use LLM to parse the prompt
    logger.info("Using LLM to parse user prompt")
    
    # Create ToolContext to access registered tools
    tools = ToolContext()
    parsed_data = _parse_with_llm(user_prompt, tools)
    
    # Extract parsed information
    vo.file_path = parsed_data.get("file_path", "")
    vo.user_extraction_strategy = parsed_data.get("extraction_strategy")
    vo.user_output_format = parsed_data.get("output_format")
    
    # Validate that we got a file path
    if not vo.file_path:
        raise ValueError(f"Could not extract file path from prompt: {user_prompt}")
    
    # Store parsing metadata
    vo.put("perceive",
           prompt_parsed=True,
           used_llm=True,
           extraction_strategy_preference=vo.user_extraction_strategy,
           output_format_preference=vo.user_output_format)
    
    # Log extracted information
    logger.info(f"Extracted file_path: {vo.file_path}")
    if vo.user_extraction_strategy:
        logger.info(f"User prefers extraction strategy: {vo.user_extraction_strategy}")
    if vo.user_output_format:
        logger.info(f"User wants output format: {vo.user_output_format}")
    
    return vo


def _parse_with_llm(prompt: str, tools) -> dict:
    """Use LLM to parse the prompt and extract structured information."""
    
    system_prompt = """You are a parser that extracts structured information from user prompts about PDF parsing.

Extract the following information:
1. file_path: The path to the PDF file (required)
2. extraction_strategy: User's preferred extraction method. Can be one of: "text", "ocr", "hybrid", "images". Only include if explicitly mentioned.
3. output_format: Description of how the user wants the output formatted. Only include if user specifies requirements like "list of skills", "extract certificates", "summary", etc.

Respond ONLY with a valid JSON object. Do not include any explanations or markdown formatting.

Example input: "this is my resume pdf 'resume/file/path', i want you to use the text extraction strategy and as output along with my parsed text structure my output such that i can clearly see list of my skills and certificates"

Example output:
{"file_path": "resume/file/path", "extraction_strategy": "text", "output_format": "list of skills and certificates"}"""

    user_msg = f"Parse this prompt: {prompt}"
    
    try:
        # Check if OpenAI tool is available
        available_llm_tools = tools.get_available_tools(category='llm')
        if 'openai' not in available_llm_tools:
            logger.error("OpenAI tool not available in registry. Please configure LLM.")
            raise ValueError("LLM tool not configured. Cannot parse prompt without LLM.")
        
        logger.info("Using OpenAI tool from registry")
        
        # Get the OpenAI tool directly from registry and execute
        # We can't use tools.execute_sync() because Prefect's event loop is already running
        import asyncio
        import concurrent.futures
        
        openai_tool = tools.registry.get_tool('openai')
        
        # Execute in a separate thread to avoid event loop conflicts
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                asyncio.run,
                openai_tool.execute(
                    prompt=user_msg,
                    system_prompt=system_prompt,
                    max_tokens=300,
                    temperature=0.0
                )
            )
            result = future.result()
        
        if result.status.value == "success":
            response_text = result.data.get("response", "{}")
            # Clean up response (remove markdown code blocks if present)
            response_text = response_text.strip()
            if response_text.startswith("```"):
                # Remove markdown code blocks
                lines = response_text.split("\n")
                response_text = "\n".join(lines[1:-1])
            
            parsed_data = json.loads(response_text)
            logger.info(f"LLM parsed data: {parsed_data}")
            return parsed_data
        else:
            logger.error(f"LLM call failed: {result.error}")
            raise ValueError(f"LLM failed to parse prompt: {result.error}")
            
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        raise ValueError(f"LLM returned invalid JSON: {e}")
    except Exception as e:
        logger.error(f"Error using LLM for prompt parsing: {e}")
        raise
