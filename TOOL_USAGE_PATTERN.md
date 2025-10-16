# Tool Usage Pattern - Correct Implementation

## Overview

The correct way to use the tool system with the agentic spine is to:
1. **Register tools** in the agent's `__init__()`
2. **Manually create ToolContext** inside stage functions when needed
3. **Use `tools.execute_sync()`** to call registered tools

## Why Not @tool_hook on Stage Functions?

The `@tool_hook` decorator is designed for standalone functions, but our stage functions are called by `agentic_spine_simple`, which expects a specific signature: `fn(ctx)`.

When we add `@tool_hook`, it changes the signature to `fn(ctx, tools)`, which breaks the spine's execution.

## Correct Pattern

### 1. Register Tools at Agent Initialization

```python
# pdf_parser_agent.py
from agent_sdk.tools.base import get_tool_registry
from agent_sdk.tools.llm import OpenAITool

class PdfParserAgent:
    def __init__(self, llm_config: Optional[Dict[str, Any]] = None):
        self.llm_config = llm_config
        
        # Register OpenAI tool in global registry
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

### 2. Use ToolContext Inside Stage Functions

```python
# parse_user_prompt.py
from agent_sdk.tools.hooks import ToolContext

@perceive
@task(name="parse_user_prompt")
def parse_user_prompt(ctx) -> PdfParserVO:  # Normal signature!
    """Parse user prompt using LLM when needed."""
    vo = ctx.data['input']
    user_prompt = vo.user_prompt
    
    # ... validation logic ...
    
    if has_preferences:
        # Create ToolContext to access registered tools
        tools = ToolContext()
        parsed_data = _parse_with_llm(user_prompt, tools)
        
        # ... process results ...
    
    return vo
```

### 3. Helper Functions Use Tools Parameter

```python
def _parse_with_llm(prompt: str, tools: ToolContext) -> dict:
    """Use LLM to parse the prompt and extract structured information."""
    
    # Check if OpenAI tool is available
    available_llm_tools = tools.get_available_tools(category='llm')
    if 'openai' not in available_llm_tools:
        logger.warning("OpenAI tool not available in registry")
        return fallback_result()
    
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
        return process_result(result)
    else:
        return fallback_result()
```

## Complete Example

### Stage Function
```python
@act
@task(name="format_custom_output")
def format_custom_output(ctx) -> PdfParserVO:
    """Format output using LLM."""
    vo = ctx.data['input']
    
    if not vo.user_output_format:
        return vo
    
    extracted_text = vo.pick("act", "extracted_text", "")
    
    # Create ToolContext when we need to use tools
    tools = ToolContext()
    formatted_output = _format_with_llm(extracted_text, vo.user_output_format, tools)
    
    vo.output_bundle["custom_formatted_output"] = formatted_output
    return vo
```

### Helper Function
```python
def _format_with_llm(text: str, format_requirement: str, tools: ToolContext) -> str:
    """Use LLM to format text."""
    
    # Check availability
    if 'openai' not in tools.get_available_tools(category='llm'):
        return "Error: OpenAI tool not configured."
    
    # Execute
    result = tools.execute_sync(
        'openai',
        prompt=f"Format this: {text}",
        system_prompt="You are a formatter...",
        max_tokens=1500,
        temperature=0.0
    )
    
    if result.status.value == "success":
        return result.data.get("response", "")
    else:
        return f"Error: {result.error}"
```

## Key Points

### ✅ DO
- Register tools in agent `__init__()`
- Create `ToolContext()` inside stage functions when needed
- Pass `tools` to helper functions
- Check tool availability before use
- Use `tools.execute_sync()` for synchronous calls

### ❌ DON'T
- Add `@tool_hook` decorator to stage functions
- Change stage function signature from `fn(ctx)`
- Create new tool instances every time
- Forget to check if tool is available

## Flow Diagram

```
Agent Initialization
    ↓
Register OpenAI tool in global registry
    ↓
User calls agent.run()
    ↓
Spine executes stage functions
    ↓
Stage function: parse_user_prompt(ctx)  ← Normal signature!
    ↓
Inside function: tools = ToolContext()  ← Create when needed
    ↓
Helper function: _parse_with_llm(prompt, tools)
    ↓
Execute: tools.execute_sync('openai', ...)
    ↓
Access registered tool from global registry
```

## Benefits

✅ **Compatible with Spine**: Functions have correct `fn(ctx)` signature  
✅ **Clean Separation**: Tool logic separated into helpers  
✅ **Lazy Creation**: ToolContext only created when needed  
✅ **Global Registry**: Tools registered once, used everywhere  
✅ **Easy Testing**: Can mock ToolContext in tests  

## Comparison: Incorrect vs Correct

### ❌ Incorrect (Breaks Spine)
```python
@perceive
@task(name="parse_user_prompt")
@tool_hook(auto_load=False)  # ← Breaks spine!
def parse_user_prompt(ctx, tools) -> PdfParserVO:  # ← Wrong signature!
    # Spine calls: fn(ctx)
    # But function expects: fn(ctx, tools)
    # Result: ERROR! Missing 'tools' parameter
```

### ✅ Correct (Works with Spine)
```python
@perceive
@task(name="parse_user_prompt")
def parse_user_prompt(ctx) -> PdfParserVO:  # ← Correct signature!
    # Spine calls: fn(ctx)
    # Function expects: fn(ctx)
    # Result: ✓ Works!
    
    # Create tools when needed
    tools = ToolContext()
    helper_function(data, tools)
```

## ToolContext API

### Creating Instance
```python
from agent_sdk.tools.hooks import ToolContext

tools = ToolContext()  # Uses global registry
```

### Checking Availability
```python
# List all tools
all_tools = tools.get_available_tools()

# List by category
llm_tools = tools.get_available_tools(category='llm')

# Check specific tool
if 'openai' in llm_tools:
    # Tool is available
```

### Executing Tools

**Synchronous:**
```python
result = tools.execute_sync('openai', 
                           prompt="Hello",
                           max_tokens=100)
```

**Asynchronous:**
```python
result = await tools.execute('openai',
                             prompt="Hello", 
                             max_tokens=100)
```

### Result Handling
```python
result = tools.execute_sync('openai', ...)

if result.status.value == "success":
    response = result.data.get("response", "")
    # Process response
else:
    error = result.error
    # Handle error
```

## Why This Pattern Works

1. **Global Registry**: Tools registered once in agent `__init__()`
2. **Normal Signatures**: Stage functions keep `fn(ctx)` signature
3. **Lazy Access**: ToolContext created only when LLM needed
4. **Clean Helpers**: Tool logic isolated in helper functions
5. **Spine Compatible**: Works perfectly with `agentic_spine_simple`

## Testing

```bash
python resume_parser_demo.py
```

**Expected output:**
```
✓ Registered OpenAI tool in registry
⚡ Stage PERCEIVE running - parse_user_prompt
Using OpenAI tool from registry
✓ Stage PERCEIVE completed
⚡ Stage ACT running - format_custom_output
Using OpenAI tool from registry
Successfully formatted output with LLM
✓ Stage ACT completed
```

## Summary

✅ **Register tools** in agent `__init__()` using `get_tool_registry()`  
✅ **Keep stage signatures** as `fn(ctx)` for spine compatibility  
✅ **Create ToolContext** manually inside stage functions  
✅ **Pass tools** to helper functions that need them  
✅ **Use execute_sync** to call registered tools  
✅ **Check availability** before executing  

This pattern gives you clean tool access while maintaining compatibility with the agentic spine! 🎉
