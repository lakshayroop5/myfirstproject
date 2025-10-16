# Intelligent Prompt-Based PDF Parser Agent

## Overview

The PDF Parser Agent now accepts **natural language prompts** instead of just file paths. This makes it more intuitive and powerful, allowing you to specify:

1. **File path** - Where your PDF is located
2. **Extraction strategy** - How you want the PDF parsed (text, OCR, hybrid, images)
3. **Output format** - How you want the results structured

## Key Features

### 🚀 Efficient LLM Usage
- **Smart Detection**: LLM is only used when your prompt contains preferences or special formatting requirements
- **Simple prompts** (just file path) → No LLM call needed
- **Complex prompts** (with preferences) → LLM used for parsing and formatting
- Uses fast models (`gpt-4o-mini`) to minimize latency

### 🎯 Extraction Strategies
- **text**: Extract text and tables from native PDF text
- **ocr**: Use OCR for scanned documents
- **hybrid**: Combine text extraction with image/table extraction
- **images**: Focus on extracting images

### 📝 Custom Output Formatting
Specify how you want your results:
- "list of skills and certificates"
- "summary with invoice number, date, and amount"
- "key terms and important clauses"
- Any custom format you need!

## Usage Examples

### Example 1: Simple File Path (No LLM)
```python
agent = PdfParserAgent()
prompt = "Parse this PDF: 'documents/report.pdf'"
result = await agent.run(prompt=prompt, session_id="session_1")
```

**What happens**: File path extracted via regex, no LLM call, fast execution!

### Example 2: Resume with Custom Output (Uses LLM)
```python
llm_config = {
    'api_key': os.getenv('OPENAI_API_KEY'),
    'model': 'gpt-4o-mini',
    'max_tokens': 1500,
    'temperature': 0.0
}
agent = PdfParserAgent(llm_config=llm_config)

prompt = """This is my resume PDF 'resumes/john_doe.pdf', 
I want you to use the text extraction strategy and as output 
along with my parsed text structure my output such that I can 
clearly see list of my skills and certificates"""

result = await agent.run(prompt=prompt, session_id="session_2")
```

**What happens**: 
1. LLM parses prompt → extracts file path, strategy="text", output format requirements
2. PDF parsed using text extraction
3. LLM formats output to show skills and certificates clearly

### Example 3: Scanned Invoice with OCR
```python
prompt = """I have a scanned invoice at 'invoices/invoice_2024.pdf', 
please use OCR to extract the text and give me a summary showing 
invoice number, date, amount, and items"""

result = await agent.run(prompt=prompt, session_id="session_3")
```

**What happens**:
1. LLM identifies OCR preference
2. Agent uses OCR extraction strategy
3. Output formatted to highlight invoice details

### Example 4: Contract with Hybrid Extraction
```python
prompt = """Parse the contract at 'contracts/agreement.pdf' using hybrid 
extraction strategy. I need to see key terms, parties involved, dates, 
and any important clauses highlighted"""

result = await agent.run(prompt=prompt, session_id="session_4")
```

## Architecture

### New Stages Added

1. **`parse_user_prompt`** (Perceive)
   - Extracts file path using regex (fast path)
   - Detects if prompt has preferences
   - Uses LLM only if needed to parse complex prompts
   
2. **`format_custom_output`** (Act)
   - Applies custom formatting to extracted content
   - Only runs if user specified output format
   - Uses LLM to intelligently structure results

### Updated Stages

3. **`select_parsing_strategy`** (Plan)
   - Now checks for user's strategy preference first
   - Falls back to automatic detection if no preference

### Pipeline Flow

```
User Prompt
    ↓
[parse_user_prompt] ← Uses LLM only if prompt has preferences
    ↓
[validate_file_path]
    ↓
[detect_pdf_type]
    ↓
[select_parsing_strategy] ← Respects user preference
    ↓
[prepare_extraction_config]
    ↓
[extract_content]
    ↓
[structure_output]
    ↓
[format_custom_output] ← Uses LLM only if custom format requested
    ↓
Result
```

## Configuration

### LLM Configuration (Optional)

Only needed if you want to use advanced features (custom output formats, strategy preferences):

```python
llm_config = {
    'api_key': 'your-openai-api-key',     # Required
    'model': 'gpt-4o-mini',                # Recommended for speed
    'max_tokens': 1500,                    # Adjust based on needs
    'temperature': 0.0                     # 0 for deterministic output
}

agent = PdfParserAgent(llm_config=llm_config)
```

### Environment Variables

```bash
export OPENAI_API_KEY="your-api-key-here"
```

Or in Python:
```python
import os
os.environ['OPENAI_API_KEY'] = 'your-api-key-here'
```

## Performance

### LLM Usage Optimization

| Scenario | LLM Calls | Latency |
|----------|-----------|---------|
| Simple path only | 0 | ~Fast (ms) |
| Path + strategy | 1 | ~1-2 seconds |
| Path + strategy + format | 2 | ~2-4 seconds |

### When LLM is NOT Used
- Prompt contains only file path
- No extraction strategy specified
- No output formatting requirements

### When LLM IS Used
- Prompt contains extraction strategy preference
- Prompt contains output format requirements
- Complex natural language prompts

## Accessing Results

```python
result = await agent.run(prompt=prompt, session_id="session_1")

# Original prompt
print(result.user_prompt)

# Extracted file path
print(result.file_path)

# User preferences
print(result.user_extraction_strategy)
print(result.user_output_format)

# Parsed content
print(result.parsed_content.text)
print(result.parsed_content.images)
print(result.parsed_content.tables)

# Custom formatted output (if requested)
if result.output_bundle.get('custom_formatted_output'):
    print(result.output_bundle['custom_formatted_output'])

# Standard output bundle
print(result.output_bundle)
```

## Error Handling

```python
try:
    result = await agent.run(prompt=prompt, session_id="session_1")
except ValueError as e:
    print(f"Invalid prompt or missing file path: {e}")
except FileNotFoundError as e:
    print(f"PDF file not found: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Best Practices

1. **For Simple Use Cases**: Just provide the file path
   ```python
   prompt = "Parse 'document.pdf'"
   ```

2. **For Specific Strategies**: Mention your preference clearly
   ```python
   prompt = "Use OCR to parse 'scanned_doc.pdf'"
   ```

3. **For Custom Output**: Describe what you want to see
   ```python
   prompt = "Parse 'resume.pdf' and show me skills, education, and experience in separate sections"
   ```

4. **API Key Management**: Use environment variables, never hardcode
   ```python
   llm_config = {'api_key': os.getenv('OPENAI_API_KEY')}
   ```

5. **Token Limits**: For large documents, output formatting is applied to first 8000 characters (~2000 tokens)

## Backward Compatibility

❌ **Breaking Change**: The old API is no longer supported:
```python
# OLD (no longer works)
result = await agent.run(file_path="document.pdf", session_id="session_1")

# NEW (required)
result = await agent.run(prompt="Parse 'document.pdf'", session_id="session_1")
```

## Troubleshooting

### Issue: LLM Not Working
**Solution**: Ensure you've provided valid LLM config and API key
```python
llm_config = {
    'api_key': os.getenv('OPENAI_API_KEY'),
    'model': 'gpt-4o-mini'
}
```

### Issue: File Path Not Extracted
**Solution**: Use quotes around the file path in your prompt
```python
# Good
prompt = "Parse this file: 'path/to/document.pdf'"

# Also good
prompt = "Parse this file: \"path/to/document.pdf\""
```

### Issue: Custom Format Not Applied
**Solution**: Make sure you initialize agent with LLM config when using custom formats
```python
agent = PdfParserAgent(llm_config=llm_config)  # Don't forget this!
```

## Running the Examples

```bash
# Set your API key (for examples with LLM)
export OPENAI_API_KEY="your-key-here"

# Run the sample client
python sample_client.py
```

Uncomment additional examples in `sample_client.py` to test different scenarios.

## Summary

The intelligent prompt feature makes the PDF parser agent:
- ✅ More intuitive and user-friendly
- ✅ Flexible with extraction strategies
- ✅ Powerful with custom output formatting
- ✅ Efficient with selective LLM usage
- ✅ Fast for simple use cases

No changes were made to the `agent_sdk` - all enhancements are in the `pdf_parser_agent` layer!
