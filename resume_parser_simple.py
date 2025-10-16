"""
Simple Resume Parser Demo
Shows clean output from the intelligent prompt-based PDF parser
"""

import asyncio
import os
from pdf_parser_agent.core.pdf_parser_agent import PdfParserAgent


async def main():
    print("\n" + "="*70)
    print("INTELLIGENT RESUME PARSER")
    print("="*70)
    
    # Configure agent
    llm_config = {
        'api_key': os.getenv('OPENAI_API_KEY', ''your_api_key''),
        'model': 'gpt-4',
        'max_tokens': 2000,
        'temperature': 0.0
    }
    
    agent = PdfParserAgent(llm_config=llm_config)
    
    # Natural language prompt
    prompt = """This is my resume PDF "C:/Users/lakshay/Downloads/tcs/projects/RenderCV_EngineeringResumes_Theme.pdf", 
    I want you to use the text extraction strategy and as output along with my 
    parsed text structure my output such that I can clearly see list of my 
    skills and certificates"""
    
    print("\n📝 Your Prompt:")
    print(f'"{prompt.strip()}"')
    
    print("\n⚙️  Processing...")
    
    try:
        result = await agent.run(prompt=prompt, session_id="demo")
        
        print("\n✅ Done!\n")
        
        # Basic info
        print("="*70)
        print("RESULTS")
        print("="*70)
        print(f"\n📄 File: {result.file_path}")
        print(f"📊 Pages: {result.output_bundle.get('page_count', 0)}")
        print(f"📝 Text: {result.output_bundle.get('parsed_content', {}).get('text_length', 0):,} characters")
        print(f"🎯 Strategy: {result.output_bundle.get('parsing_strategy', 'N/A')}")
        
        # Show complete parsed content
        print("\n" + "="*70)
        print("📄 COMPLETE PARSED CONTENT")
        print("="*70)
        
        raw_text = result.output_bundle.get('parsed_content', {}).get('text', '')
        if raw_text:
            print(f"\n{raw_text}")
            print(f"\n{'-'*70}")
            print(f"Total: {len(raw_text):,} characters")
        else:
            print("\n❌ No text extracted")
        
        # Show what was requested
        print("\n" + "="*70)
        print("🎯 WHAT YOU ASKED FOR")
        print("="*70)
        
        if result.user_output_format:
            print(f'\nYou requested: "{result.user_output_format}"')
        else:
            print("\nNo specific format requested")
        
        # The main output - formatted by LLM (THE EXACT PART REQUESTED)
        print("\n" + "="*70)
        print("✨ YOUR REQUESTED OUTPUT (Formatted by LLM)")
        print("="*70)
        
        custom_output = result.output_bundle.get('custom_formatted_output')
        if custom_output:
            print(f"\n{custom_output}\n")
        else:
            print("\n❌ No custom formatted output available")
        
        print("\n" + "="*70)
        print("✓ Resume parsed successfully!")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
