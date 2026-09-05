"""Typed creator-domain failures converted to capability results at the edge."""


class CreatorDomainError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
