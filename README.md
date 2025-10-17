# PDF Parser Agent

An intelligent, LLM-powered PDF parsing agent that understands natural language prompts and extracts content with custom formatting capabilities.

## 🌟 Features

- **Natural Language Interface**: Describe what you want in plain English
- **Intelligent Prompt Parsing**: Automatically extracts file paths, extraction strategies, and output format preferences from user prompts
- **Multiple Extraction Strategies**: 
  - Text extraction for native PDFs
  - OCR for scanned documents
  - Image extraction
  - Table detection and extraction
  - Hybrid approaches
- **Auto-Detection**: Automatically detects PDF type (native vs scanned) and selects optimal strategy
- **LLM-Powered Output Formatting**: Custom formatting of extracted content based on user requirements
- **Agentic Architecture**: Built on a perceive-plan-act framework with Prefect orchestration
- **Comprehensive Monitoring**: Track execution flow, metrics, and stage-by-stage processing

## 📋 Requirements

### System Requirements
- Python 3.10 or higher
- Windows, macOS, or Linux

### Python Dependencies
```
prefect>=3.0.0
pydantic>=2.0.0
openai>=1.0.0
pypdf2>=3.0.0
pdf2image>=1.16.0
pytesseract>=0.3.10
pillow>=10.0.0
tabula-py>=2.8.0
fastapi>=0.100.0
httpx>=0.24.0
```

### External Dependencies
- **Tesseract OCR**: Required for scanned PDF processing
  - Windows: Download from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)
  - macOS: `brew install tesseract`
  - Linux: `sudo apt-get install tesseract-ocr`
- **Java**: Required for table extraction with tabula-py
  - Download from [java.com](https://www.java.com/)

## 🚀 Installation

1. **Clone or download the project**
   ```bash
   cd pdf_parser_agent_project
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install external dependencies**
   - Install Tesseract OCR (see requirements above)
   - Install Java Runtime Environment

## 📖 How to Run the Demo

### Resume Parser Demo

The `resume_parser_demo.py` demonstrates intelligent resume parsing with natural language prompts.

```bash
python resume_parser_demo.py
```

**What the demo does:**
1. Initializes the agent with GPT-4
2. Parses a natural language prompt like:
   ```
   "This is my resume PDF at path/to/resume.pdf, 
   I want you to use the text extraction strategy and 
   output a list of my skills and certificates"
   ```
3. Automatically extracts:
   - File path
   - Extraction strategy preference
   - Output format requirements
4. Processes the PDF through perceive-plan-act stages
5. Formats the output according to user requirements

### Custom Usage

```python
import asyncio
from pdf_parser_agent.core.pdf_parser_agent import PdfParserAgent

async def parse_pdf():
    # Configure the agent
    llm_config = {
        'api_key': 'your-openai-api-key',
        'model': 'gpt-4',
        'max_tokens': 2000,
        'temperature': 0.0
    }
    
    agent = PdfParserAgent(llm_config=llm_config)
    
    # Use natural language to describe what you want
    prompt = """
    Parse my invoice at 'documents/invoice.pdf',
    use text extraction and give me a summary with
    total amount, invoice date, and line items
    """
    
    # Run the agent
    result = await agent.run(
        prompt=prompt,
        session_id="custom_session_001"
    )
    
    # Access results
    print(f"Extracted text length: {result['output_bundle']['parsed_content']['text_length']}")
    print(f"Custom formatted output: {result['output_bundle'].get('custom_formatted_output')}")

# Run
asyncio.run(parse_pdf())
```

## 🏗️ Architecture

### Agentic Framework (Perceive-Plan-Act)

```
┌─────────────┐
│  PERCEIVE   │  - Parse user prompt (LLM)
│             │  - Validate file path
│             │  - Detect PDF type
└──────┬──────┘
       │
┌──────▼──────┐
│    PLAN     │  - Select parsing strategy
│             │  - Prepare extraction config
└──────┬──────┘
       │
┌──────▼──────┐
│     ACT     │  - Extract content
│             │  - Structure output
│             │  - Format custom output (LLM)
└─────────────┘
```

### Project Structure

```
pdf_parser_agent_project/
├── pdf_parser_agent/
│   ├── core/
│   │   └── pdf_parser_agent.py       # Main agent class
│   ├── stages/
│   │   ├── perceive/
│   │   │   ├── parse_user_prompt.py  # LLM-based prompt parsing
│   │   │   ├── validate_file_path.py # File validation
│   │   │   └── detect_pdf_type.py    # PDF type detection
│   │   ├── plan/
│   │   │   ├── select_parsing_strategy.py
│   │   │   └── prepare_extraction_config.py
│   │   └── act/
│   │       ├── extract_content.py
│   │       ├── structure_output.py
│   │       └── format_custom_output.py
│   ├── services/
│   │   └── pdf_service.py            # PDF processing utilities
│   └── util/
│       └── asyncio_orchestrator.py   # Workflow orchestration
├── agent_sdk/                         # Agentic framework SDK
│   ├── core/
│   │   ├── spine.py                   # Workflow execution engine
│   │   ├── stages.py                  # Stage decorators
│   │   ├── context.py                 # Context management
│   │   └── state.py                   # State monitoring
│   └── tools/
│       ├── base.py                    # Tool registry
│       └── llm.py                     # LLM tool (OpenAI)
├── resume_parser_demo.py              # Demo script
└── README.md
```

## 🎯 Key Concepts

### 1. Natural Language Prompts
Instead of passing multiple parameters, describe what you want:
```python
prompt = """
Parse 'report.pdf' using OCR and 
extract all tables in CSV format
"""
```

### 2. Automatic Strategy Selection
The agent automatically detects if a PDF is:
- **Native** (contains text) → Uses text extraction
- **Scanned** (image-based) → Uses OCR
- **Hybrid** → Combines multiple methods

### 3. Custom Output Formatting
Request specific output formats in natural language:
- "List of skills and certificates"
- "Summary with key metrics"
- "Table of line items with totals"

### 4. Stage-Based Processing
Each stage has a specific purpose:
- **Perceive**: Understand input and environment
- **Plan**: Decide on strategy and configuration
- **Act**: Execute and format output

## 🔧 Configuration

### LLM Configuration
```python
llm_config = {
    'api_key': 'your-key',
    'model': 'gpt-4',           # or 'gpt-4o-mini' for faster/cheaper
    'max_tokens': 2000,         # Adjust based on needs
    'temperature': 0.0          # 0 for deterministic, higher for creative
}
```

### Extraction Strategies
- **text**: Fast, works with native PDFs
- **ocr**: Slower, works with scanned documents
- **hybrid**: Combines text + OCR + images
- **images**: Extracts only images

## 📊 Output Format

The agent returns a dictionary with:
```python
{
    'file_path': 'path/to/file.pdf',
    'session_id': 'session_001',
    'user_prompt': 'original prompt',
    'user_extraction_strategy': 'text',
    'user_output_format': 'list of skills',
    'stage_data': {
        'perceive': {...},
        'plan': {...},
        'act': {...}
    },
    'parsed_content': {
        'text': 'extracted text...',
        'images': [...],
        'tables': [...],
        'metadata': {...}
    },
    'output_bundle': {
        'parsing_strategy': 'text',
        'pdf_type': 'native',
        'page_count': 5,
        'parsed_content': {
            'text': '...',
            'text_length': 12345,
            'image_count': 0,
            'table_count': 2
        },
        'custom_formatted_output': 'LLM-formatted output...'
    }
}
```

## 🐛 Troubleshooting

### Common Issues

**1. OpenAI API Error 403**
- Ensure your API key is valid
- Check if you need to configure a private endpoint
- Verify your OpenAI account has available credits

**2. File Not Found**
- Use absolute paths in your prompts
- Check file exists at the specified location
- Ensure file has `.pdf` extension

## 🙏 Acknowledgments

Built using:
- [Prefect](https://www.prefect.io/) - Workflow orchestration
- [OpenAI](https://openai.com/) - LLM capabilities
- [PyPDF2](https://pypdf2.readthedocs.io/) - PDF processing
- [Tesseract](https://github.com/tesseract-ocr/tesseract) - OCR engine
- [tabula-py](https://github.com/chezou/tabula-py) - Table extraction

---