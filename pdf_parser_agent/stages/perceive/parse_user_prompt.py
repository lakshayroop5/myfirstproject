import json
import re
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
    Parse the user's natural language prompt to extract:
    - File path
    - Extraction strategy preference (optional)
    - Output format requirements (optional)
    
    Uses LLM only if the prompt contains preferences beyond just a file path.
    """
    vo = ctx.data['input']
    user_prompt = vo.user_prompt
    
    if not user_prompt:
        raise ValueError("user_prompt is required")
    
    # Fast path: Try to extract file path using regex first
    file_path = _extract_file_path_regex(user_prompt)
    
    # Check if prompt contains strategy or format preferences
    has_preferences = _has_extraction_preferences(user_prompt)
    
    if has_preferences:
        # Use LLM to parse complex prompt with preferences
        logger.info("Prompt contains preferences, using LLM to parse")
        # Create ToolContext to access registered tools
        tools = ToolContext()
        parsed_data = _parse_with_llm(user_prompt, tools)
        
        # Override file_path if LLM found a better one
        if parsed_data.get("file_path"):
            file_path = parsed_data["file_path"]
        
        vo.file_path = file_path
        vo.user_extraction_strategy = parsed_data.get("extraction_strategy")
        vo.user_output_format = parsed_data.get("output_format")
        
        vo.put("perceive",
               prompt_parsed=True,
               used_llm=True,
               extraction_strategy_preference=vo.user_extraction_strategy,
               output_format_preference=vo.user_output_format)
    else:
        # Simple case: just file path, no LLM needed
        logger.info("Simple prompt with only file path, skipping LLM")
        vo.file_path = file_path
        vo.put("perceive",
               prompt_parsed=True,
               used_llm=False)
    
    if not vo.file_path:
        raise ValueError(f"Could not extract file path from prompt: {user_prompt}")
    
    logger.info(f"Extracted file_path: {vo.file_path}")
    if vo.user_extraction_strategy:
        logger.info(f"User prefers extraction strategy: {vo.user_extraction_strategy}")
    if vo.user_output_format:
        logger.info(f"User wants output format: {vo.user_output_format}")
    
    return vo


def _extract_file_path_regex(prompt: str) -> str:
    """Extract file path using regex patterns."""
    # Common patterns for file paths
    patterns = [
        r"['\"]([^'\"]+\.pdf)['\"]",  # Quoted paths
        r"([A-Za-z]:[/\\][^\s,]+\.pdf)",  # Windows absolute paths
        r"(/[^\s,]+\.pdf)",  # Unix absolute paths
        r"([\w/\\.-]+\.pdf)",  # Relative paths
    ]
    
    for pattern in patterns:
        match = re.search(pattern, prompt, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return ""


def _has_extraction_preferences(prompt: str) -> bool:
    """Check if prompt contains extraction strategy or output format preferences."""
    prompt_lower = prompt.lower()
    
    # Strategy keywords
    strategy_keywords = ["ocr", "text extraction", "extract text", "image extraction", 
                        "hybrid", "scanning", "scanned", "strategy"]
    
    # Format keywords
    format_keywords = ["format", "output", "structure", "list", "table", "json", 
                      "summary", "highlight", "extract", "show me", "i want", "need"]
    
    return any(keyword in prompt_lower for keyword in strategy_keywords + format_keywords)


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
            logger.warning("OpenAI tool not available in registry")
            return {"file_path": _extract_file_path_regex(prompt)}
        
        logger.info("Using OpenAI tool from registry")
        
        # Execute LLM call using the tool registry
        result = tools.execute_sync(
            'openai',
            prompt=user_msg,
            system_prompt=system_prompt,
            max_tokens=300,
            temperature=0.0
        )
        
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
            logger.warning(f"LLM call failed: {result.error}")
            # Fallback to regex
            return {"file_path": _extract_file_path_regex(prompt)}
            
    except Exception as e:
        logger.warning(f"Error using LLM for prompt parsing: {e}")
        # Fallback to regex
        return {"file_path": _extract_file_path_regex(prompt)}
