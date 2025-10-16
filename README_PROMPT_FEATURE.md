# 🚀 Intelligent Prompt-Based PDF Parser Agent

Your PDF parser agent is now **intelligent**! It accepts natural language prompts instead of just file paths.

## Quick Start

### Simple Usage (No LLM Required)
```python
from pdf_parser_agent import PdfParserAgent

agent = PdfParserAgent()
result = await agent.run(
    prompt="Parse this PDF: 'path/to/document.pdf'",
    session_id="session_1"
)
```

### Advanced Usage (With LLM)
```python
import os
from pdf_parser_agent import PdfParserAgent

# Configure LLM
llm_config = {
    'api_key': os.getenv('OPENAI_API_KEY'),
    'model': 'gpt-4o-mini',
    'max_tokens': 1500,
    'temperature': 0.0
}

agent = PdfParserAgent(llm_config=llm_config)

# Use natural language with preferences
result = await agent.run(
    prompt="""This is my resume PDF 'resume.pdf', 
    use text extraction and show me list of skills and certificates""",
    session_id="session_1"
)

# Access formatted output
print(result.output_bundle['custom_formatted_output'])
```

## Key Features

✅ **Natural Language Input**: No need to pass separate parameters  
✅ **Smart LLM Usage**: Only used when needed (efficient!)  
✅ **Strategy Control**: Specify text, OCR, hybrid, or image extraction  
✅ **Custom Formatting**: Get output structured your way  
✅ **Fast for Simple Cases**: Regex-based parsing when no LLM needed  

## What Can You Say?

### File Path Only
- `"Parse 'document.pdf'"`
- `"Extract content from 'report.pdf'"`
- `"Process C:/Users/docs/invoice.pdf"`

### With Extraction Strategy
- `"Use OCR to parse 'scanned_doc.pdf'"`
- `"Extract text from 'contract.pdf' using hybrid strategy"`
- `"Parse 'image_doc.pdf' with text extraction"`

### With Custom Output
- `"Parse 'resume.pdf' and list my skills and education"`
- `"Extract from 'invoice.pdf' and show invoice number, date, amount"`
- `"Get key terms from 'contract.pdf' in bullet points"`

### Complete Example
```
"This is my resume PDF 'resumes/john.pdf', 
I want you to use the text extraction strategy and 
structure the output to clearly show my skills, 
education, and work experience"
```

## When is LLM Used?

| Scenario | LLM Calls | Speed |
|----------|-----------|-------|
| Just file path | ❌ 0 | Fast (ms) |
| + Strategy preference | ✅ 1 | ~1-2s |
| + Custom formatting | ✅ 2 | ~2-4s |

## Configuration

### Option 1: Environment Variable (Recommended)
```bash
export OPENAI_API_KEY="your-api-key-here"
```

```python
import os
llm_config = {
    'api_key': os.getenv('OPENAI_API_KEY'),
    'model': 'gpt-4o-mini'
}
agent = PdfParserAgent(llm_config=llm_config)
```

### Option 2: Direct Configuration
```python
llm_config = {
    'api_key': 'your-api-key-here',  # Not recommended for production
    'model': 'gpt-4o-mini',
    'max_tokens': 1500,
    'temperature': 0.0
}
agent = PdfParserAgent(llm_config=llm_config)
```

### Option 3: No LLM (Simple Parsing)
```python
agent = PdfParserAgent()  # No config needed
# Can only use simple prompts with file paths
```

## Running Examples

```bash
# Run the sample client
python sample_client.py

# For LLM examples, set your API key first
export OPENAI_API_KEY="your-key"
python sample_client.py
# Then uncomment additional examples in the file
```

## Accessing Results

```python
result = await agent.run(prompt="...", session_id="...")

# Original prompt
print(result.user_prompt)

# Extracted information
print(result.file_path)
print(result.user_extraction_strategy)
print(result.user_output_format)

# Parsed content (same as before)
print(result.parsed_content.text)
print(result.parsed_content.images)
print(result.parsed_content.tables)

# Custom formatted output (new!)
if 'custom_formatted_output' in result.output_bundle:
    print(result.output_bundle['custom_formatted_output'])
```

## Migration from Old API

**Old way (no longer works):**
```python
result = await agent.run(file_path="doc.pdf", session_id="s1")
```

**New way (required):**
```python
result = await agent.run(prompt="Parse 'doc.pdf'", session_id="s1")
```

## Architecture Overview

```
User Prompt
    ↓
[Parse Prompt] ─────┐
    ↓               │ Uses LLM only if
[Validate Path]     │ preferences detected
    ↓               │
[Detect PDF Type]   │
    ↓               ↓
[Select Strategy] ←─┘ (respects user preference)
    ↓
[Extract Content]
    ↓
[Structure Output]
    ↓
[Format Output] ─────┐
    ↓               │ Uses LLM only if
Result              │ custom format requested
                    ↓
```

## Error Handling

```python
try:
    result = await agent.run(prompt=prompt, session_id="s1")
except ValueError as e:
    print(f"Invalid prompt: {e}")
except FileNotFoundError as e:
    print(f"File not found: {e}")
except Exception as e:
    print(f"Error: {e}")
```

## Best Practices

1. **Use environment variables** for API keys
2. **Quote file paths** in your prompts: `'path/to/file.pdf'`
3. **Keep it simple** if you don't need LLM features
4. **Be specific** about output requirements for best results
5. **Check documentation** for more examples: `INTELLIGENT_PROMPT_GUIDE.md`

## Documentation

- **`INTELLIGENT_PROMPT_GUIDE.md`** - Comprehensive guide with examples
- **`CHANGES.md`** - Detailed list of all changes made
- **`sample_client.py`** - Working code examples

## What Changed?

### New Files
- `pdf_parser_agent/stages/perceive/parse_user_prompt.py`
- `pdf_parser_agent/stages/act/format_custom_output.py`

### Updated Files
- `pdf_parser_agent/core/pdf_parser_agent.py` - New API
- `pdf_parser_agent/vo/pdf_parser_vo.py` - New fields
- `pdf_parser_agent/stages/plan/select_parsing_strategy.py` - User preferences

### Unchanged
- ✅ `agent_sdk/` - No changes (as requested)
- ✅ Other stages and services remain unchanged

## Support

For issues or questions:
1. Check `INTELLIGENT_PROMPT_GUIDE.md` for detailed examples
2. Review `sample_client.py` for working code
3. Read `CHANGES.md` for migration details

## Summary

Your agent is now more intelligent and user-friendly while remaining efficient. LLM is used strategically only when needed, ensuring fast performance for simple operations while providing powerful features for complex requirements.

**Enjoy your intelligent PDF parser! 🎉**
