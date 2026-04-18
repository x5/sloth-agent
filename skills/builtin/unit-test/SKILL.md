---
name: unit-test
source: builtin
trigger: manual
version: 1.0.0
description: Unit testing best practices and patterns
---

# Unit Testing

Write tests that are fast, reliable, and maintainable:

## Test Structure (Arrange-Act-Assert)
```python
def test_user_requires_email():
    # Arrange
    data = {"name": "Test User"}

    # Act
    with pytest.raises(ValidationError):
        User.create(data)

    # Assert
    # Exception confirms required field validation
```

## Naming
- `test_[unit]_[scenario]_[expected_behavior]`
- Example: `test_login_invalid_password_returns_error`

## What to Test
- Public API behavior (not internal implementation)
- Edge cases: empty, null, boundary values, large input
- Error paths: invalid input, missing dependencies, timeouts

## What NOT to Test
- Framework internals (trust the framework)
- Third-party library behavior (test your integration, not their code)
- Trivial getters/setters
- Tests that only test the mock

## Patterns
- Use fixtures for shared setup, not base classes
- Parametrize for testing multiple inputs
- Mock only external dependencies (DB, HTTP, filesystem)
- Prefer integration tests for complex workflows

## Rules
- Tests must be deterministic (no flaky tests)
- Each test should verify ONE thing
- If a test is hard to read, the code is probably hard to use
- Keep test suite fast — under 10 seconds total for unit tests
