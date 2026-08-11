import re

# Prompt Injection Attack Patterns
INJECTION_PATTERNS = [
    r"ignore (previous|all) (instructions|directions)",
    r"system prompt",
    r"reveal your (secret|key|instructions)",
    r"you are now (dan|unfiltered|jailbroken)",
    r"bypass (guardrails|safety)",
    r"override (system|rules)",
]



def sanitize_user_input(prompt: str) -> tuple[bool, str]:
    """
    Inspects user input for prompt injection payloads or malicious overrides.
    Returns (is_safe: bool, sanitized_prompt_or_error: str).
    """
    clean_prompt = prompt.strip()
    if not clean_prompt:
        return False, "Prompt cannot be empty."

    # Check against prompt injection patterns
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, clean_prompt, re.IGNORECASE):
            return False, "[SECURITY ALERT]: Potential prompt injection detected. Your query has been blocked."

    # Enforce maximum prompt length
    if len(clean_prompt) > 1000:
        clean_prompt = clean_prompt[:1000]

    return True, clean_prompt
