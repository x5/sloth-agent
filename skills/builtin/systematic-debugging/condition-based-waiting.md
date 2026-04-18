# Condition-Based Waiting

## Overview

Flaky tests often guess at timing with arbitrary delays. This creates race conditions where tests pass on fast machines but fail under load or in CI.

**Core principle:** Wait for the actual condition you care about, not a guess about how long it takes.

## When to Use

Use when:
- Tests have arbitrary delays (`time.sleep()`, `asyncio.sleep()`)
- Tests are flaky (pass sometimes, fail under load)
- Tests timeout when run in parallel
- Waiting for async operations to complete

Don't use when:
- Testing actual timing behavior (debounce, throttle intervals)
- Always document WHY if using arbitrary timeout

## Core Pattern

```python
# BEFORE: Guessing at timing
time.sleep(0.5)
result = get_result()
assert result is not None

# AFTER: Waiting for condition
result = wait_for(get_result, description="result to be ready")
assert result is not None
```

## Quick Patterns

| Scenario | Pattern |
|----------|---------|
| Wait for file | `wait_for(lambda: os.path.exists(path))` |
| Wait for state | `wait_for(lambda: machine.state == 'ready')` |
| Wait for count | `wait_for(lambda: len(items) >= 5)` |
| Wait for process | `wait_for(lambda: process.poll() is not None)` |
| Wait for output | `wait_for(lambda: len(stdout.readlines()) > 0)` |
| Complex condition | `wait_for(lambda: obj.ready and obj.value > 10)` |

## Implementation

Generic polling function:
```python
import time
from typing import Callable, TypeVar

T = TypeVar('T')

def wait_for(
    condition: Callable[[], T],
    description: str = "condition",
    timeout: float = 5.0,
    interval: float = 0.01,
) -> T:
    """Poll condition until it returns a truthy value or timeout expires."""
    start = time.monotonic()

    while True:
        result = condition()
        if result:
            return result

        if time.monotonic() - start > timeout:
            raise TimeoutError(
                f"Timeout waiting for {description} after {timeout}s"
            )

        time.sleep(interval)  # Poll every 10ms
```

## Common Mistakes

**Polling too fast:** `time.sleep(0.001)` - wastes CPU
**Fix:** Poll every 10ms (`interval=0.01`)

**No timeout:** Loop forever if condition never met
**Fix:** Always include timeout with clear error

**Stale data:** Cache state before loop
**Fix:** Call getter inside loop for fresh data

## When Arbitrary Timeout IS Correct

```python
# Tool ticks every 100ms - need 2 ticks to verify partial output
wait_for(lambda: manager.is_started, description="tool to start")
time.sleep(0.2)   # 200ms = 2 ticks at 100ms intervals - documented and justified
```

**Requirements:**
1. First wait for triggering condition
2. Based on known timing (not guessing)
3. Comment explaining WHY

## Real-World Impact

From debugging sessions:
- Fixed flaky tests across multiple files
- Pass rate: 60% -> 100%
- Execution time: 40% faster
- No more race conditions
