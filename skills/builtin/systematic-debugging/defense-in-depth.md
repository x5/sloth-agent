# Defense-in-Depth Validation

## Overview

When you fix a bug caused by invalid data, adding validation at one place feels sufficient. But that single check can be bypassed by different code paths, refactoring, or mocks.

**Core principle:** Validate at EVERY layer data passes through. Make the bug structurally impossible.

## Why Multiple Layers

Single validation: "We fixed the bug"
Multiple layers: "We made the bug impossible"

Different layers catch different cases:
- Entry validation catches most bugs
- Business logic catches edge cases
- Environment guards prevent context-specific dangers
- Debug logging helps when other layers fail

## The Four Layers

### Layer 1: Entry Point Validation
**Purpose:** Reject obviously invalid input at API boundary

```python
def create_project(name: str, working_directory: str) -> Project:
    if not working_directory or working_directory.strip() == '':
        raise ValueError('working_directory cannot be empty')
    if not os.path.exists(working_directory):
        raise FileNotFoundError(f'working_directory does not exist: {working_directory}')
    if not os.path.isdir(working_directory):
        raise ValueError(f'working_directory is not a directory: {working_directory}')
    # ... proceed
```

### Layer 2: Business Logic Validation
**Purpose:** Ensure data makes sense for this operation

```python
def initialize_workspace(project_dir: str, session_id: str) -> Workspace:
    if not project_dir:
        raise ValueError('project_dir required for workspace initialization')
    # ... proceed
```

### Layer 3: Environment Guards
**Purpose:** Prevent dangerous operations in specific contexts

```python
def git_init(directory: str) -> None:
    # In tests, refuse git init outside temp directories
    if os.environ.get('PYTEST_CURRENT_TEST'):
        tmp_dir = tempfile.gettempdir()
        if not os.path.abspath(directory).startswith(os.path.abspath(tmp_dir)):
            raise ValueError(
                f'Refusing git init outside temp dir during tests: {directory}'
            )
    # ... proceed
```

### Layer 4: Debug Instrumentation
**Purpose:** Capture context for forensics

```python
def git_init(directory: str) -> None:
    import traceback
    logger.debug('About to git init', {
        'directory': directory,
        'cwd': os.getcwd(),
        'stack': traceback.format_stack(),
    })
    # ... proceed
```

## Applying the Pattern

When you find a bug:

1. **Trace the data flow** - Where does bad value originate? Where used?
2. **Map all checkpoints** - List every point data passes through
3. **Add validation at each layer** - Entry, business, environment, debug
4. **Test each layer** - Try to bypass layer 1, verify layer 2 catches it

## Key Insight

All four layers were necessary. During testing, each layer caught bugs the others missed:
- Different code paths bypassed entry validation
- Mocks bypassed business logic checks
- Edge cases on different platforms needed environment guards
- Debug logging identified structural misuse

**Don't stop at one validation point.** Add checks at every layer.
