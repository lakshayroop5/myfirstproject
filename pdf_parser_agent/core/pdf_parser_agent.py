from typing import Optional, Dict, Any
from agent_sdk import agentic_spine, agentic_spine_simple
from agent_sdk.tools.base import get_tool_registry
from agent_sdk.tools.llm import OpenAITool
from pdf_parser_agent.stages.perceive.parse_user_prompt import parse_user_prompt
from pdf_parser_agent.stages.perceive.validate_file_path import validate_file_path
from pdf_parser_agent.stages.perceive.detect_pdf_type import detect_pdf_type
from pdf_parser_agent.stages.plan.select_parsing_strategy import select_parsing_strategy
from pdf_parser_agent.stages.plan.prepare_extraction_config import prepare_extraction_config
from pdf_parser_agent.stages.act.extract_content import extract_content
from pdf_parser_agent.stages.act.structure_output import structure_output
from pdf_parser_agent.stages.act.format_custom_output import format_custom_output

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
        
        # Register OpenAI tool in the tool registry if llm_config is provided
        if llm_config:
            self._register_llm_tool(llm_config)
    
    def _register_llm_tool(self, llm_config: Dict[str, Any]):
        """Register the OpenAI LLM tool in the global tool registry."""
        registry = get_tool_registry()
        
        # Check if already registered
        if 'openai' not in registry.list_tools():
            openai_tool = OpenAITool(name='openai', config=llm_config)
            registry.register(openai_tool, category='llm')
            print(f"✓ Registered OpenAI tool in registry")
    
    async def run(self, prompt: str, session_id: str) -> Dict[str, Any]:
        """
        Run the PDF parser agent with a natural language prompt.
        
        Args:
            prompt: Natural language prompt containing file path and preferences.
                   Example: "Parse my resume at 'path/to/resume.pdf', extract text 
                            and show me list of skills and certificates"
            session_id: Unique session identifier
            
        Returns:
            Dictionary with parsed content and output
        """
        context_dict = {
            'user_prompt': prompt,
            'session_id': session_id,
            'file_path': '',
            'container': {'llm_config': self.llm_config} if self.llm_config else {},
            'user_extraction_strategy': None,
            'user_output_format': None,
            'stage_data': {},
            'meta': {},
            'parsed_content': {
                'text': '',
                'images': [],
                'tables': [],
                'metadata': {}
            },
            'sources': [],
            'output_bundle': {}
        }

        result_context = await agentic_spine(
            input_data=context_dict,
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

        # Return the result (check if it's an object with .data or direct dict)
        if hasattr(result_context, 'data'):
            return result_context.data.get('input', result_context.data)
        else:
            return result_context