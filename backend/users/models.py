from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models

from .constants import NAME_MAX_LENGTH


class CustomUser(AbstractUser):
    email = models.EmailField(
        verbose_name='Email',
        unique=True,
        help_text=(
            'Укажите e-mail. '
            'E-mail не должен превышать 254 символов.'
        )
    )
    username = models.CharField(
        verbose_name='Логин',
        max_length=NAME_MAX_LENGTH,
        validators=(UnicodeUsernameValidator(),),
        unique=True,
        help_text=(
            'Укажите логин пользователя. '
            'Используйте буквы, цифры и символы @/./+/-/_. '
            'Логин не может начинаться цифрой и превышать 150 символов.'
        )
    )
    first_name = models.CharField(
        verbose_name='Имя',
        max_length=NAME_MAX_LENGTH,
        help_text='Укажите имя.'
    )
    last_name = models.CharField(
        verbose_name='Фамилия',
        max_length=NAME_MAX_LENGTH,
        help_text='Укажите фамилию.'
    )
    avatar = models.ImageField(
        verbose_name='Фото профиля',
        upload_to='users/',
        null=True,
        blank=True,
        help_text='Добавьте фото профиля.'
    )
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ('username', 'first_name', 'last_name')

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        default_related_name = 'users',
        ordering = ('username',)

    def __str__(self):
        return self.username


class Follow(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='followers',
        verbose_name='Подписчик'
    )
    following = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='followings',
        verbose_name='Пользователь'
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        default_related_name = 'followers',
        ordering = ('user',)
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'following'),
                name='unique_user_following_pair'
            ),
            models.CheckConstraint(
                name='users_cannot_follow_themselves',
                check=~models.Q(user=models.F('following')),
            ),
        ]

    def __str__(self):
        return f'{self.user.username} подписан на {self.following.username}'
