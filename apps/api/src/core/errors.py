class DomainError(Exception):
    """Expected business-rule failure."""


class NotFoundError(DomainError):
    pass


class ConflictError(DomainError):
    pass


class AuthenticationError(DomainError):
    pass


class RateLimitedError(DomainError):
    pass
