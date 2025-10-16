from typing import Optional, Dict, Any
from agent_sdk import agentic_spine, agentic_spine_simple
from pdf_parser_agent.stages.perceive.parse_user_prompt import parse_user_prompt
from pdf_parser_agent.stages.perceive.validate_file_path import validate_file_path
from pdf_parser_agent.stages.perceive.detect_pdf_type import detect_pdf_type
from pdf_parser_agent.stages.plan.select_parsing_strategy import select_parsing_strategy
from pdf_parser_agent.stages.plan.prepare_extraction_config import prepare_extraction_config
from pdf_parser_agent.stages.act.extract_content import extract_content
from pdf_parser_agent.stages.act.structure_output import structure_output
from pdf_parser_agent.stages.act.format_custom_output import format_custom_output
from pdf_parser_agent.vo.pdf_parser_vo import PdfParserVO

class PdfParserAgent:
    def __init__(self, llm_config: Optional[Dict[str, Any]] = None):
        """
        Initialize the PDF Parser Agent.
        
        Args:
            llm_config: Configuration for LLM (OpenAI, etc.)
                       Example: {
                           'api_key': 'your-api-key',
                           'model': 'gpt-4o-mini',
                           'max_tokens': 1000,
                           'temperature': 0.0
                       }
        """
        self.llm_config = llm_config
    
    async def run(self, prompt: str, session_id: str) -> PdfParserVO:
        """
        Run the PDF parser agent with a natural language prompt.
        
        Args:
            prompt: Natural language prompt containing file path and preferences.
                   Example: "Parse my resume at 'path/to/resume.pdf', extract text 
                            and show me list of skills and certificates"
            session_id: Unique session identifier
            
        Returns:
            PdfParserVO with parsed content and output
        """
        vo = PdfParserVO(
            user_prompt=prompt,
            session_id=session_id,
            container={'llm_config': self.llm_config} if self.llm_config else None
        )

        result_context = agentic_spine_simple(
            input_data=vo,
            functions=[
                parse_user_prompt,       # NEW: Parse natural language prompt
                validate_file_path,
                detect_pdf_type,
                select_parsing_strategy,  # UPDATED: Now considers user preferences
                prepare_extraction_config,
                extract_content,
                structure_output,
                format_custom_output,     # NEW: Apply custom formatting if requested
            ],
        )

        # Extract the actual VO from the context
        return result_context.data['input']