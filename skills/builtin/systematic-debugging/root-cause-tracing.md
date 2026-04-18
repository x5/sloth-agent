# Root Cause Tracing

## Overview

Bugs often manifest deep in the call stack. Your instinct is to fix where the error appears, but that's treating a symptom.

**Core principle:** Trace backward through the call chain until you find the original trigger, then fix at the source.

## When to Use

Use when:
- Error happens deep in execution (not at entry point)
- Stack trace shows long call chain
- Unclear where invalid data originated
- Need to find which test/code triggers the problem

## The Tracing Process

### 1. Observe the Symptom

Example error output from pytest:
```
E   FileNotFoundError: [Errno 2] No such file or directory: '/tmp/missing'
tests/test_pipeline.py:42: FileNotFoundError
```

### 2. Find Immediate Cause

What code directly causes this?
```python
with open(config['output_path'], 'w') as f:  # output_path = '/tmp/missing'
```

### 3. Ask: What Called This?

```python
save_results(config['output_path'], data)
  -> called by Pipeline.run()
  -> called by Runner.execute()
  -> called by test at test_pipeline.py
```

### 4. Keep Tracing Up

What value was passed?
- `config['output_path']` was never set, defaulted to empty string
- Empty string resolved to current working directory

### 5. Find Original Trigger

Where did the missing config come from?
```python
config = load_config()  # Returns {} if file not found
config.setdefault('output_path', '')  # Default should not be empty
```

**Root cause:** Default value for missing config key is empty string, should be None with validation.

## Adding Stack Traces

When you can't trace manually, add instrumentation:

```python
import traceback

def save_results(path, data):
    if not path:
        traceback.print_stack()
        print(f"DEBUG save_results: empty path, cwd={os.getcwd()}")

    with open(path, 'w') as f:
        f.write(data)
```

**Critical:** Log BEFORE the dangerous operation, not after it fails.

**Capture output:**
```bash
uv run pytest tests/test_pipeline.py -v -s 2>&1 | grep "DEBUG"
```

**Analyze stack traces:**
- Look for test file names
- Find the line number triggering the call
- Identify the pattern (same test? same parameter?)

## Finding Which Test Causes Pollution

If something appears during tests but you don't know which test:

Use the bisection script `find_polluter.py` in this directory:

```bash
python scripts/find_polluter.py "output/results.json" "tests/**/test_*.py"
```

Runs tests one-by-one, stops at first polluter.

## Key Principle

**NEVER fix just where the error appears.** Trace back to find the original trigger.

## Stack Trace Tips

**In tests:** Use `print()` or `logging.debug()` - loggers may be suppressed
**Before operation:** Log before the dangerous operation, not after it fails
**Include context:** File paths, environment variables, timestamps
**Capture stack:** `traceback.print_stack()` shows complete call chain
