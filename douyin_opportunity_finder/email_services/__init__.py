"""Email services package."""

from .email_sender import EmailService, create_email_service_from_env, parse_email_list

__all__ = ['EmailService', 'create_email_service_from_env', 'parse_email_list']
