from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.validators import (MaxLengthValidator, MaxValueValidator,
                                    MinValueValidator)
from django.db import models
from django.template.defaultfilters import slugify

from .constants import (MAX_COOKING_TIME, MAX_INGREDIENT_AMOUNT,
                        MAX_INGREDIENT_LENGTH, MAX_MEASUREMENT_UNIT,
                        MIN_AMOUNT_TIME, NAME_MAX_LENGTH, TAG_MAX_LENGTH)

User = get_user_model()


class Tag(models.Model):
    name = models.CharField(
        verbose_name='Тег',
        max_length=TAG_MAX_LENGTH,
        validators=(MaxLengthValidator,),
        unique=True,
        help_text='Укажите название тега'
    )
    slug = models.SlugField(
        verbose_name='Слаг',
        max_length=TAG_MAX_LENGTH,
        validators=(MaxLengthValidator,),
        unique=True,
        help_text='Укажите слаг'
    )

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
        ordering = ('name',)
        default_related_name = 'tags'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Ingredient(models.Model):
    name = models.CharField(
        verbose_name='Ингредиент',
        max_length=MAX_INGREDIENT_LENGTH,
        validators=(MaxLengthValidator,),
        help_text='Укажите ингредиент'
    )
    measurement_unit = models.CharField(
        verbose_name='Единица измерения',
        max_length=MAX_MEASUREMENT_UNIT,
        validators=(MaxLengthValidator,),
        help_text='Укажите единицу измерения'
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        ordering = ('name',)
        default_related_name = 'ingredients'
        constraints = [
            models.UniqueConstraint(
                fields=('name', 'measurement_unit'),
                name='unique_ingredient_name_measurement_unit_pair'
            )
        ]

    def __str__(self):
        return self.name


class Recipe(models.Model):
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор рецепта',
    )
    name = models.CharField(
        verbose_name='Рецепт',
        max_length=NAME_MAX_LENGTH,
        validators=(MaxLengthValidator,),
        help_text='Укажите название рецепта'
    )
    text = models.TextField(
        verbose_name='Описание рецепта',
        help_text='Добавьте описание рецепта'
    )
    cooking_time = models.PositiveIntegerField(
        validators=(
            MaxValueValidator(MAX_COOKING_TIME),
            MinValueValidator(MIN_AMOUNT_TIME)
        ),
        verbose_name='Время приготовления',
        help_text='Укажите время приготовления (не менее 1 минуты)'
    )
    image = models.ImageField(
        verbose_name='Изображение блюда',
        upload_to='recipes/images/',
        help_text='Добавьте фото готового блюда'
    )
    tags = models.ManyToManyField(
        Tag,
        verbose_name='Тег рецепта',
        help_text='Укажите тег'
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        verbose_name='Ингредиенты рецепта',
        help_text='Добавьте ингредиенты и их количество'
    )
    created_at = models.DateTimeField(
        verbose_name='Дата публикации',
        auto_now_add=True
    )

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        default_related_name = 'recipes'
        constraints = [
            models.UniqueConstraint(
                fields=('name', 'author'),
                name='unique_recipe_name_author_pair'
            )
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return f'{settings.SITE_URL_PREFIX}recipes/{self.pk}/'


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        verbose_name='Ингредиент'
    )
    amount = models.PositiveSmallIntegerField(
        validators=(
            MaxValueValidator(MAX_INGREDIENT_AMOUNT),
            MinValueValidator(MIN_AMOUNT_TIME)
        ),
        verbose_name='Количество ингредиента в рецепте',
        help_text='Укажите количество'
    )

    class Meta:
        verbose_name = 'Ингредиент рецепта'
        verbose_name_plural = 'Ингредиенты рецепта'
        default_related_name = 'ingredient_recipe'
        constraints = [
            models.UniqueConstraint(
                fields=('recipe', 'ingredient'),
                name='unique_recipe_ingredient_pair'
            )
        ]

    def __str__(self):
        return (
            f'{self.ingredient.name}: {self.amount}'
            f'{self.ingredient.measurement_unit}'
        )


class UserRecipeBaseModel(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт'
    )

    class Meta:
        ordering = ('recipe__name',)
        abstract = True

    def __str__(self):
        return (
            f' {self.user.username} добавил {self.recipe} в '
            f'{self._meta.verbose_name}'
        )


class Favorites(UserRecipeBaseModel):
    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = verbose_name
        default_related_name = 'favorites'
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='favorites_unique_user_recipe_pair'
            ),
        ]


class ShoppingCart(UserRecipeBaseModel):
    class Meta:
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Списки покупок'
        default_related_name = 'shopping_cart'
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='shopping_cart_unique_user_recipe_pair'
            ),
        ]
