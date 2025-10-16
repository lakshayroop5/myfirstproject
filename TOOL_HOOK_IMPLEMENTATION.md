# Tool Hook Implementation - Clean Pattern

## Overview

Refactored LLM usage to properly use the `@tool_hook` decorator following the SDK's intended pattern, where tools are pre-registered in the global tool registry and accessed via the `tools` parameter.

## Architecture

```
PdfParserAgent.__init__()
    ↓
Register OpenAI tool in global registry
    ↓
Stage functions decorated with @tool_hook
    ↓
Tools auto-injected via 'tools' parameter
    ↓
Execute via tools.execute_sync('openai', ...)
```

## Key Changes

### 1. **Agent Initialization** (`pdf_parser_agent.py`)

**Added:**
- OpenAI tool registration in `__init__()`
- Tool registry import
- `_register_llm_tool()` helper method

```python
from agent_sdk.tools.base import get_tool_registry
from agent_sdk.tools.llm import OpenAITool

class PdfParserAgent:
    def __init__(self, llm_config: Optional[Dict[str, Any]] = None):
        self.llm_config = llm_config
        
        # Register OpenAI tool in the tool registry
        if llm_config:
            self._register_llm_tool(llm_config)
    
    def _register_llm_tool(self, llm_config: Dict[str, Any]):
        """Register the OpenAI LLM tool in the global tool registry."""
        registry = get_tool_registry()
        
        if 'openai' not in registry.list_tools():
            openai_tool = OpenAITool(name='openai', config=llm_config)
            registry.register(openai_tool, category='llm')
            print(f"✓ Registered OpenAI tool in registry")
```

### 2. **Parse User Prompt** (`parse_user_prompt.py`)

**Changes:**
- Added `@tool_hook(auto_load=False)` decorator
- Added `tools` parameter to function signature
- Simplified `_parse_with_llm()` to just accept `tools`
- Removed manual tool creation and async handling
- Use `tools.execute_sync('openai', ...)` directly

**Before:**
```python
@perceive
@task(name="parse_user_prompt")
def parse_user_prompt(ctx) -> PdfParserVO:
    # ...
    parsed_data = _parse_with_llm(user_prompt, ctx)

def _parse_with_llm(prompt: str, ctx) -> dict:
    llm = OpenAITool(name="prompt_parser", config=llm_config)
    # Complex async handling with ThreadPoolExecutor...
    result = executor.submit(asyncio.run, llm.execute(...)).result()
```

**After:**
```python
@perceive
@task(name="parse_user_prompt")
@tool_hook(auto_load=False)
def parse_user_prompt(ctx, tools) -> PdfParserVO:
    # ...
    parsed_data = _parse_with_llm(user_prompt, tools)

def _parse_with_llm(prompt: str, tools) -> dict:
    # Check if tool is available
    if 'openai' not in tools.get_available_tools(category='llm'):
        return {"file_path": _extract_file_path_regex(prompt)}
    
    # Simple, clean execution
    result = tools.execute_sync('openai', 
                               prompt=user_msg,
                               system_prompt=system_prompt,
                               max_tokens=300,
                               temperature=0.0)
```

### 3. **Format Custom Output** (`format_custom_output.py`)

**Changes:**
- Added `@tool_hook(auto_load=False)` decorator
- Added `tools` parameter to function signature
- Simplified `_format_with_llm()` to just accept `tools`
- Removed manual tool creation and async handling
- Use `tools.execute_sync('openai', ...)` directly

**Before:**
```python
@act
@task(name="format_custom_output")
def format_custom_output(ctx) -> PdfParserVO:
    # ...
    formatted_output = _format_with_llm(extracted_text, vo.user_output_format, ctx)

def _format_with_llm(text: str, format_requirement: str, ctx) -> str:
    llm = OpenAITool(name="output_formatter", config=llm_config)
    # Complex async handling...
```

**After:**
```python
@act
@task(name="format_custom_output")
@tool_hook(auto_load=False)
def format_custom_output(ctx, tools) -> PdfParserVO:
    # ...
    formatted_output = _format_with_llm(extracted_text, vo.user_output_format, tools)

def _format_with_llm(text: str, format_requirement: str, tools) -> str:
    # Check if tool is available
    if 'openai' not in tools.get_available_tools(category='llm'):
        return "Error: OpenAI tool not configured."
    
    # Simple execution
    result = tools.execute_sync('openai',
                               prompt=user_msg,
                               system_prompt=system_prompt,
                               max_tokens=1500,
                               temperature=0.0)
```

## How It Works

### 1. **Tool Registration** (Startup)
```python
# When agent is initialized
agent = PdfParserAgent(llm_config={'api_key': '...', 'model': 'gpt-4'})

# Internally registers:
registry = get_tool_registry()
registry.register(OpenAITool(name='openai', config=llm_config), category='llm')
```

### 2. **Tool Injection** (Runtime)
```python
# The @tool_hook decorator automatically injects 'tools' parameter
@tool_hook(auto_load=False)
def my_stage(ctx, tools):  # 'tools' is auto-injected!
    pass
```

### 3. **Tool Execution** (Usage)
```python
# Check availability
available = tools.get_available_tools(category='llm')  # ['openai']

# Execute synchronously
result = tools.execute_sync('openai', prompt="...", max_tokens=100)

# Or execute asynchronously (if function is async)
result = await tools.execute('openai', prompt="...", max_tokens=100)
```

## Benefits

### ✅ **Cleaner Code**
- No manual tool instantiation
- No complex async/event loop handling
- No ThreadPoolExecutor boilerplate
- Single line tool execution

### ✅ **SDK Compliant**
- Uses `@tool_hook` decorator as intended
- Follows framework patterns
- Integrates with tool registry system

### ✅ **Centralized Management**
- Tools registered once at initialization
- Available throughout agent lifecycle
- Easy to list and inspect tools

### ✅ **Extensibility**
- Easy to add more LLM providers
- Can check available tools at runtime
- Fallback to alternative tools

### ✅ **Better Error Handling**
- Check tool availability before use
- Clear error messages if tool not configured
- Graceful fallbacks

## Decorator Stacking

The decorators work together:

```python
@perceive           # Stage type (PERCEIVE)
@task               # Prefect task wrapper
@tool_hook          # Tool injection
def my_stage(ctx, tools):
    pass
```

**Order matters:**
1. `@perceive` - Marks as PERCEIVE stage
2. `@task` - Wraps as Prefect task
3. `@tool_hook` - Injects tools parameter

## Tool Discovery

You can check available tools at runtime:

```python
# List all tools
all_tools = tools.get_available_tools()

# List LLM tools only
llm_tools = tools.get_available_tools(category='llm')

# Check specific tool
if 'openai' in llm_tools:
    result = tools.execute_sync('openai', ...)
```

## Execution Methods

### Synchronous (for sync functions)
```python
result = tools.execute_sync('openai', 
                           prompt="Hello",
                           max_tokens=100)
```

### Asynchronous (for async functions)
```python
result = await tools.execute('openai',
                             prompt="Hello", 
                             max_tokens=100)
```

## Error Handling Pattern

```python
def _parse_with_llm(prompt: str, tools) -> dict:
    # 1. Check tool availability
    if 'openai' not in tools.get_available_tools(category='llm'):
        logger.warning("OpenAI tool not available")
        return fallback_result()
    
    # 2. Execute with try/except
    try:
        result = tools.execute_sync('openai', ...)
        
        # 3. Check result status
        if result.status.value == "success":
            return process_success(result)
        else:
            logger.warning(f"LLM failed: {result.error}")
            return fallback_result()
            
    except Exception as e:
        logger.error(f"Error: {e}")
        return fallback_result()
```

## Configuration Flow

```
User creates agent
    ↓
llm_config = {
    'api_key': '...',
    'model': 'gpt-4',
    'max_tokens': 1000
}
    ↓
agent = PdfParserAgent(llm_config)
    ↓
OpenAI tool registered with config
    ↓
Stages access tool via 'openai' name
    ↓
All LLM calls use same configuration
```

## Auto-load Parameter

```python
@tool_hook(auto_load=False)  # We use False
```

- `auto_load=True`: Loads tools from config files
- `auto_load=False`: Manual registration (our approach)

We use `False` because:
- Tools registered programmatically
- Configuration comes from user at runtime
- More control over tool lifecycle

## Comparison

### Old Pattern (Manual)
```python
# ❌ Manual tool creation every time
llm = OpenAITool(name="...", config=llm_config)

# ❌ Complex async handling
with ThreadPoolExecutor() as executor:
    result = executor.submit(asyncio.run, llm.execute(...)).result()

# ❌ Repeated boilerplate
```

### New Pattern (Tool Hook)
```python
# ✅ Tool pre-registered
# (done once in agent.__init__)

# ✅ Simple execution
result = tools.execute_sync('openai', ...)

# ✅ Clean and readable
```

## Testing

The refactored code works exactly as before:

```bash
python resume_parser_demo.py
```

**Expected output:**
- ✓ OpenAI tool registered in registry
- ✓ Using OpenAI tool from registry
- ✓ Successfully formatted output with LLM
- ✓ All functionality preserved

## Future Enhancements

With this pattern, you can easily:

### 1. Add Multiple LLM Providers
```python
# In agent.__init__
if llm_config:
    self._register_llm_tool(llm_config)

if gemini_config:
    gemini_tool = GeminiTool(name='gemini', config=gemini_config)
    registry.register(gemini_tool, category='llm')
```

### 2. Fallback to Alternative LLMs
```python
# Try OpenAI, fallback to Gemini
for llm_name in ['openai', 'gemini', 'mistral']:
    if llm_name in tools.get_available_tools(category='llm'):
        result = tools.execute_sync(llm_name, ...)
        if result.is_success:
            return result
```

### 3. Dynamic Tool Selection
```python
# User specifies which LLM to use
preferred_llm = ctx.get('preferred_llm', 'openai')
if preferred_llm in tools.get_available_tools(category='llm'):
    result = tools.execute_sync(preferred_llm, ...)
```

## Summary

✅ **Registered OpenAI tool** in agent initialization  
✅ **Decorated stages** with `@tool_hook`  
✅ **Removed manual tool creation** and async complexity  
✅ **Simplified execution** to `tools.execute_sync('openai', ...)`  
✅ **Added tool availability checks** for better error handling  
✅ **Follows SDK patterns** and best practices  
✅ **Cleaner, more maintainable code**  

The implementation now properly leverages the agent SDK's tool system! 🎉
