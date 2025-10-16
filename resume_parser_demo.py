"""
Resume Parser Demo - Intelligent Prompt-Based PDF Parser

This demo shows how to use natural language to parse a resume PDF
and get structured output with skills and certificates highlighted.
"""

import asyncio
import os
from pdf_parser_agent.core.pdf_parser_agent import PdfParserAgent


async def parse_resume_with_intelligent_prompt():
    """
    Demo: Parse a resume using natural language prompt
    
    Features demonstrated:
    1. Natural language input with file path, strategy, and output format
    2. Automatic extraction of user preferences
    3. LLM-based custom output formatting
    4. Structured results
    """
    
    print("\n" + "="*80)
    print("INTELLIGENT RESUME PARSER - DEMO")
    print("="*80)
    
    # =============================================================================
    # STEP 1: Configure the Agent with LLM
    # =============================================================================
    print("\n📋 Step 1: Configuring Agent with LLM")
    print("-" * 80)
    
    llm_config = {
        'api_key': os.getenv('OPENAI_API_KEY', ''your_api_key''),
        'model': 'gpt-4',  # Using GPT-4 for best quality
        'max_tokens': 2000,
        'temperature': 0.0  # Deterministic output
    }
    
    agent = PdfParserAgent(llm_config=llm_config)
    print("✓ Agent initialized with GPT-4")
    print("✓ LLM will be used for: prompt parsing & output formatting")
    
    # =============================================================================
    # STEP 2: Create Natural Language Prompt
    # =============================================================================
    print("\n📝 Step 2: Natural Language Prompt")
    print("-" * 80)
    
    prompt = """This is my resume PDF "C:/Users/lakshay/Downloads/tcs/projects/RenderCV_EngineeringResumes_Theme.pdf", 
    I want you to use the text extraction strategy and as output along with my 
    parsed text structure my output such that I can clearly see list of my 
    skills and certificates"""
    
    print("Prompt:")
    print(f"  \"{prompt.strip()}\"")
    print("\nWhat the agent will extract from this prompt:")
    print("  • File path: RenderCV_EngineeringResumes_Theme.pdf")
    print("  • Extraction strategy: text")
    print("  • Output format: list of skills and certificates")
    
    # =============================================================================
    # STEP 3: Run the Agent
    # =============================================================================
    print("\n⚙️  Step 3: Processing Resume")
    print("-" * 80)
    
    try:
        result = await agent.run(prompt=prompt, session_id="resume_demo_001")
        
        # =============================================================================
        # STEP 4: Display Results
        # =============================================================================
        print("\n✅ Step 4: Processing Complete!")
        print("=" * 80)
        
        # Show extracted metadata
        print("\n📊 EXTRACTION METADATA")
        print("-" * 80)
        print(f"File Path:          {result.file_path}")
        print(f"Session ID:         {result.session_id}")
        print(f"Strategy Used:      {result.output_bundle.get('parsing_strategy', 'N/A')}")
        print(f"PDF Type:           {result.output_bundle.get('pdf_type', 'N/A')}")
        print(f"Page Count:         {result.output_bundle.get('page_count', 0)}")
        print(f"LLM Used:           {result.pick('perceive', 'used_llm', False)}")
        print(f"Custom Format:      {result.pick('act', 'custom_format_applied', False)}")
        
        # Show extraction statistics
        print("\n📈 EXTRACTION STATISTICS")
        print("-" * 80)
        parsed_data = result.output_bundle.get('parsed_content', {})
        print(f"Text Length:        {parsed_data.get('text_length', 0):,} characters")
        print(f"Images Extracted:   {parsed_data.get('image_count', 0)}")
        print(f"Tables Extracted:   {parsed_data.get('table_count', 0)}")
        
        # Show extraction methods used
        extraction_methods = result.pick('plan', 'extraction_methods', [])
        print(f"Extraction Methods: {', '.join(extraction_methods)}")
        
        # Show FULL parsed content
        print("\n📄 COMPLETE PARSED CONTENT (Raw Extraction)")
        print("=" * 80)
        raw_text = parsed_data.get('text', '')
        if raw_text:
            print(raw_text)
            print("\n" + "-" * 80)
            print(f"Total length: {len(raw_text):,} characters")
        else:
            print("No text extracted")
        
        # Show what user requested in the prompt
        print("\n🎯 WHAT YOU ASKED FOR IN YOUR PROMPT:")
        print("=" * 80)
        if result.user_output_format:
            print(f"You requested: \"{result.user_output_format}\"")
        else:
            print("No specific output format was requested")
        
        # Show custom formatted output (THE EXACT PART REQUESTED)
        print("\n✨ YOUR REQUESTED OUTPUT (LLM-Formatted)")
        print("=" * 80)
        print("This is the exact information you asked for, extracted and formatted by LLM:\n")
        
        custom_output = result.output_bundle.get('custom_formatted_output')
        if custom_output:
            print(custom_output)
        else:
            print("❌ No custom formatted output available")
            print("   This may happen if:")
            print("   • LLM failed to parse the prompt")
            print("   • Output formatting was not requested")
            print("   • There was an error during formatting")
        
        # Show user preferences that were extracted
        print("\n🔍 USER PREFERENCES EXTRACTED FROM PROMPT")
        print("-" * 80)
        print(f"Original Prompt:      {result.user_prompt[:80]}...")
        print(f"Extraction Strategy:  {result.user_extraction_strategy or 'Auto-detected'}")
        print(f"Output Format:        {result.user_output_format or 'Default'}")
        
        # Show stage execution summary
        print("\n⏱️  STAGE EXECUTION SUMMARY")
        print("-" * 80)
        print("✓ PERCEIVE stages:")
        print(f"  • parse_user_prompt      - Extracted file path and preferences")
        print(f"  • validate_file_path     - File exists: {result.pick('perceive', 'file_valid', False)}")
        print(f"  • detect_pdf_type        - Type: {result.pick('perceive', 'pdf_type', 'unknown')}")
        print("\n✓ PLAN stages:")
        print(f"  • select_parsing_strategy - Strategy: {result.output_bundle.get('parsing_strategy')}")
        print(f"  • prepare_extraction_config - Config prepared")
        print("\n✓ ACT stages:")
        print(f"  • extract_content        - Extracted {parsed_data.get('text_length', 0)} chars")
        print(f"  • structure_output       - Structured into output bundle")
        print(f"  • format_custom_output   - Applied custom formatting: {result.pick('act', 'custom_format_applied', False)}")
        
        # Success summary
        print("\n" + "=" * 80)
        print("🎉 SUCCESS! Resume parsed and formatted intelligently")
        print("=" * 80)
        print("\nKey Benefits Demonstrated:")
        print("  ✓ Natural language input (no need for multiple parameters)")
        print("  ✓ Intelligent preference extraction (strategy + format)")
        print("  ✓ Custom output formatting (skills & certificates highlighted)")
        print("  ✓ Efficient LLM usage (only 2 calls: parse + format)")
        print("  ✓ Complete metadata and statistics")
        
        return result
        
    except FileNotFoundError as e:
        print(f"\n❌ ERROR: File not found")
        print(f"   {e}")
        print("\n💡 Make sure the PDF file exists at the specified path")
        
    except ValueError as e:
        print(f"\n❌ ERROR: Invalid prompt or configuration")
        print(f"   {e}")
        print("\n💡 Check your prompt format and LLM configuration")
        
    except Exception as e:
        print(f"\n❌ ERROR: Unexpected error occurred")
        print(f"   {e}")
        print("\n🔍 Full traceback:")
        import traceback
        traceback.print_exc()


async def main():
    """Run the resume parser demo"""
    print("\n" + "╔" + "="*78 + "╗")
    print("║" + " "*78 + "║")
    print("║" + "  INTELLIGENT PDF PARSER AGENT - RESUME PARSING DEMO".center(78) + "║")
    print("║" + " "*78 + "║")
    print("╚" + "="*78 + "╝")
    
    print("\nThis demo shows how to parse a resume using natural language prompts.")
    print("The agent will:")
    print("  1. Extract file path from your prompt")
    print("  2. Understand your extraction strategy preference")
    print("  3. Parse the PDF using the appropriate method")
    print("  4. Format the output according to your requirements")
    
    await parse_resume_with_intelligent_prompt()
    
    print("\n" + "="*80)
    print("Demo completed! Check the output above for results.")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
