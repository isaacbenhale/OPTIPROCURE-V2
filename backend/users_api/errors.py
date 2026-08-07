"""Exceptions métier de la Lambda users_api — mappées en codes HTTP par handler.py."""


class ApiError(Exception):
    """Base commune : code HTTP, code d'erreur machine, message, champs en défaut."""

    status_code = 500
    code = "INTERNAL_ERROR"

    def __init__(self, message, fields=None):
        super().__init__(message)
        self.message = message
        self.fields = fields or {}


class ValidationError(ApiError):
    status_code = 400
    code = "VALIDATION_ERROR"


class UnauthorizedError(ApiError):
    status_code = 401
    code = "UNAUTHORIZED"


class ForbiddenError(ApiError):
    status_code = 403
    code = "FORBIDDEN"


class NotFoundError(ApiError):
    status_code = 404
    code = "NOT_FOUND"


class ConflictError(ApiError):
    status_code = 409
    code = "CONFLICT"
