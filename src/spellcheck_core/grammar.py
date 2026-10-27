"""Grammar checking configuration (local LanguageTool server, fully free)."""

# Server limits raised so no request is ever throttled or rejected.
# These configure the LOCAL LanguageTool server that `language_tool_python`
# starts - no paid account, no API key, no remote server involved.
LT_CONFIG = {
    "maxTextLength": 500_000,               # chars per request
    "maxTextHardLength": 500_000,           # hard cap before the server refuses
    "maxCheckTimeMillis": 60_000,           # ms allowed per check
    "maxSpellingSuggestions": 5,
    "requestLimit": 5_000,                  # requests per period
    "requestLimitPeriodInSeconds": 86_400,  # period = 24 h
}
