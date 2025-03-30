from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxLengthValidator
from django.db import models

from .constants import EMAIL_MAX_LENGTH, NAME_MAX_LENGTH
from .validators import validate_email, validate_username


class CustomUser(AbstractUser):
    email = models.EmailField(
        verbose_name='Email',
        max_length=EMAIL_MAX_LENGTH,
        validators=(
            MaxLengthValidator, validate_email
        ),
        unique=True,
        help_text='Укажите e-mail'
    )
    username = models.CharField(
        verbose_name='Логин',
        max_length=NAME_MAX_LENGTH,
        validators=(
            MaxLengthValidator, validate_username
        ),
        unique=True,
        help_text='Укажите логин пользователя'
    )
    first_name = models.CharField(
        verbose_name='Имя',
        max_length=NAME_MAX_LENGTH,
        validators=(MaxLengthValidator,),
        help_text='Укажите имя'
    )
    last_name = models.CharField(
        verbose_name='Фамилия',
        max_length=NAME_MAX_LENGTH,
        validators=(MaxLengthValidator,),
        help_text='Укажите фамилию'
    )
    avatar = models.ImageField(
        verbose_name='Фото профиля',
        upload_to='users/',
        null=True,
        blank=True,
        help_text='Добавьте фото профиля'
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
