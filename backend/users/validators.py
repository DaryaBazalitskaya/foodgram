import re

from django.core.exceptions import ValidationError

from .constants import EMAIL_MAX_LENGTH, NAME_MAX_LENGTH


def validate_username(username):
    """Проверка логина."""
    if username.lower() == 'me':
        raise ValidationError(
            'Вы не можете использовать "me" в качестве логина.'
        )
    if not re.fullmatch(r'^[\w.@+-]+$', username):
        raise ValidationError(
            'Логин содержит недопустимые символы.'
        )
    if len(username) > NAME_MAX_LENGTH:
        raise ValidationError(
            f'Логин превышает допустимую длину в '
            f'{NAME_MAX_LENGTH} символов.'
        )
    return username


def validate_email(email):
    """Проверка email."""
    if len(email) > EMAIL_MAX_LENGTH:
        raise ValidationError(
            f'Email превышает допустимую длину в '
            f'{EMAIL_MAX_LENGTH} символов.'
        )
    return email
