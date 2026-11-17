"""Domain errors. The API layer (main.py) maps them to HTTP responses."""


class DomainError(Exception):
    status_code = 400

    def __init__(self, detail: str):
        """Store the client-facing German/English error message on `.detail`."""
        super().__init__(detail)
        self.detail = detail


class NotFoundError(DomainError):
    status_code = 404
