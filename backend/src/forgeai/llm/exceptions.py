class LLMError(Exception):
    """Base exception for all LLM-related failures."""


class LLMAuthenticationError(LLMError):
    """Raised when provider authentication fails."""


class LLMRateLimitError(LLMError):
    """Raised when the provider rate limit is exceeded."""


class LLMTimeoutError(LLMError):
    """Raised when an LLM request times out."""


class LLMConnectionError(LLMError):
    """Raised when the provider cannot be reached."""


class LLMProviderError(LLMError):
    """Raised when the provider returns an unexpected error."""


class LLMResponseError(LLMError):
    """Raised when the provider returns an invalid response."""
