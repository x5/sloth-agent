"""Role-to-tools mapping. Defines the base tool sets each agent role gets."""

ROLE_BASE_TOOLS: dict[str, list[str]] = {
    "lead": ["read", "grep"],
    "bazi": ["read", "grep"],
    "ziwei": ["read", "grep"],
    "iching": ["read", "grep"],
    "astrologer": ["read", "grep"],
    "fortune": ["read", "read_range", "glob", "grep", "grep_repo", "ls_dir"],
}
