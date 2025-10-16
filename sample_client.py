import asyncio
import json
import os
from pdf_parser_agent.core.pdf_parser_agent import PdfParserAgent


async def example_1_simple_prompt():
    """Example 1: Simple prompt with just a file path"""
    print("\n" + "="*70)
    print("EXAMPLE 1: Simple file path (no LLM needed)")
    print("="*70)
    
    # Initialize agent (no LLM config needed for simple prompts)
    agent = PdfParserAgent()
    
    prompt = "Parse this PDF: 'C:/Users/2784572/Downloads/pdf_parser_agent/example.pdf'"
    
    try:
        result = await agent.run(prompt=prompt, session_id="session_1")
        print(f"\n✓ Extracted {len(result.parsed_content.text)} characters")
        print(f"✓ Strategy used: {result.output_bundle.get('parsing_strategy')}")
    except Exception as e:
        print(f"✗ Error: {e}")


async def example_2_resume_with_requirements():
    """Example 2: Resume parsing with specific output requirements (uses LLM)"""
    print("\n" + "="*70)
    print("EXAMPLE 2: Resume with custom output format (uses LLM)")
    print("="*70)
    
    # Initialize agent with LLM config
    llm_config = {
        'api_key': os.getenv('OPENAI_API_KEY', ''your_api_key''),
        'model': 'gpt-4o-mini',
        'max_tokens': 1500,
        'temperature': 0.0
    }
    agent = PdfParserAgent(llm_config=llm_config)
    
    prompt = """This is my resume PDF "C:/Users/lakshay/Downloads/tcs/projects/RenderCV_EngineeringResumes_Theme.pdf", 
    I want you to use the text extraction strategy and as output along with my 
    parsed text structure my output such that I can clearly see list of my 
    skills and certificates"""
    
    try:
        result = await agent.run(prompt=prompt, session_id="session_2")
        
        print(f"\n✓ File parsed: {result.file_path}")
        print(f"✓ Strategy: {result.output_bundle.get('parsing_strategy')}")
        print(f"✓ Used LLM: {result.pick('perceive', 'used_llm')}")
        
        # Display custom formatted output
        if result.output_bundle.get('custom_formatted_output'):
            print("\n--- Custom Formatted Output ---")
            print(result.output_bundle['custom_formatted_output'])
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()


async def example_3_invoice_ocr():
    """Example 3: Scanned invoice with OCR preference"""
    print("\n" + "="*70)
    print("EXAMPLE 3: Scanned invoice with OCR (uses LLM for parsing prompt)")
    print("="*70)
    
    llm_config = {
        'api_key': os.getenv('OPENAI_API_KEY', ''your_api_key''),
        'model': 'gpt-4o-mini',
        'max_tokens': 1500,
        'temperature': 0.0
    }
    agent = PdfParserAgent(llm_config=llm_config)
    
    prompt = """I have a scanned invoice at 'invoices/invoice_2024.pdf', 
    please use OCR to extract the text and give me a summary showing 
    invoice number, date, amount, and items"""
    
    try:
        result = await agent.run(prompt=prompt, session_id="session_3")
        
        print(f"\n✓ File: {result.file_path}")
        print(f"✓ Strategy: {result.output_bundle.get('parsing_strategy')}")
        print(f"✓ User requested: {result.user_extraction_strategy}")
        
        if result.output_bundle.get('custom_formatted_output'):
            print("\n--- Extracted Information ---")
            print(result.output_bundle['custom_formatted_output'])
            
    except Exception as e:
        print(f"✗ Error: {e}")


async def example_4_contract_hybrid():
    """Example 4: Contract with hybrid extraction"""
    print("\n" + "="*70)
    print("EXAMPLE 4: Contract with hybrid extraction")
    print("="*70)
    
    llm_config = {
        'api_key': os.getenv('OPENAI_API_KEY', ''your_api_key''),
        'model': 'gpt-4',
        'max_tokens': 1500,
        'temperature': 0.0
    }
    agent = PdfParserAgent(llm_config=llm_config)
    
    prompt = """Parse the contract at 'contracts/agreement.pdf' using hybrid 
    extraction strategy. I need to see key terms, parties involved, dates, 
    and any important clauses highlighted"""
    
    try:
        result = await agent.run(prompt=prompt, session_id="session_4")
        
        print(f"\n✓ File: {result.file_path}")
        print(f"✓ Strategy: {result.output_bundle.get('parsing_strategy')}")
        print(f"✓ Extraction methods: {result.pick('plan', 'extraction_methods')}")
        
    except Exception as e:
        print(f"✗ Error: {e}")


async def main():
    """Run all examples"""
    print("\n" + "="*70)
    print("PDF PARSER AGENT - INTELLIGENT PROMPT EXAMPLES")
    print("="*70)
    print("\nThis agent now accepts natural language prompts!")
    print("Features:")
    print("  • Extracts file path from your prompt")
    print("  • Understands extraction strategy preferences (text, OCR, hybrid)")
    print("  • Formats output according to your requirements")
    print("  • Uses LLM only when needed (efficient!)")
    
    # Run examples
    # await example_1_simple_prompt()
    
    # Uncomment to run examples that require LLM
    # Make sure to set OPENAI_API_KEY environment variable
    
    await example_2_resume_with_requirements()
    # await example_3_invoice_ocr()
    # await example_4_contract_hybrid()
    
    print("\n" + "="*70)
    print("All examples completed!")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())