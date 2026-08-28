class DomainError(Exception):
    """Base exception for domain-level errors."""
    pass

class ValidationError(Exception):
    """Exception raised for validation errors in the business logic."""
    pass
