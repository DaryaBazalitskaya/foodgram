import base64

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import transaction
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from recipes.models import (Favorites, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag, UserRecipeBaseModel)
from users.models import Follow

User = get_user_model()


class Base64ImageField(serializers.ImageField):
    """Поле для изображения."""
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
        return super().to_internal_value(data)


class UserAvatarSerializer(serializers.ModelSerializer):
    """Сериализатор для работы с фото профиля."""
    avatar = Base64ImageField()

    class Meta:
        model = User
        fields = ('avatar',)

    def update(self, instance, validated_data):
        instance.avatar = validated_data.get('avatar', instance.avatar)
        instance.save()
        return instance

    def to_representation(self, instance):
        if instance.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(instance.avatar.url)
            else:
                return instance.avatar.url
        return None


class SubscribeRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор отображения рецептов пользователя:
    в списке рецептов автора, избранном и списке покупок."""

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class UserReadSerializer(serializers.ModelSerializer):
    """Сериализатор пользователя для чтения."""
    avatar = Base64ImageField()
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'first_name',
            'last_name', 'is_subscribed', 'avatar',
        )

    def get_is_subscribed(self, obj):
        """Подписан ли текущий пользователь на автора рецепта."""
        request = self.context.get('request')
        return bool(
            request and request.user
            and obj.followings.filter(
                user=request.user.id
            ).exists()
        )


class UserSubscriptionsListSerializer(UserReadSerializer):
    """Сериализатор пользователя для отображения поля
    рецептов и поля их количества."""
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta(UserReadSerializer):
        model = User
        fields = UserReadSerializer.Meta.fields + (
            'recipes', 'recipes_count',
        )

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes_limit = request.GET.get('recipes_limit')
        recipes_list = obj.recipes.all()
        if recipes_limit is not None:
            try:
                recipes_limit = int(recipes_limit)
                if recipes_limit <= 0:
                    raise serializers.ValidationError(
                        'recipes_limit должен быть положительным числом.'
                    )
                recipes_list = recipes_list[:recipes_limit]
            except ValueError:
                raise serializers.ValidationError(
                    'recipes_limit должен быть числом.'
                )
        return SubscribeRecipeSerializer(
            recipes_list,
            context=self.context,
            many=True
        ).data

    def get_recipes_count(self, user):
        """Количество рецептов автора."""
        return user.recipes.count()


class UserListSerializer(serializers.ModelSerializer):
    """Сериализатор списка пользователей."""
    avatar = Base64ImageField(allow_null=True)

    class Meta:
        model = User
        fields = (
            'id', 'username', 'first_name', 'last_name', 'email', 'avatar'
        )


class FollowSerializer(serializers.ModelSerializer):
    """Сериализатор модели Follow."""
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        default=serializers.CurrentUserDefault
    )

    class Meta:
        model = Follow
        fields = ('user', 'following',)
        read_only_fields = ('user',)
        validators = [
            UniqueTogetherValidator(
                queryset=Follow.objects.all(),
                fields=('user', 'following'),
                message='Вы уже подписаны на этого пользователя!'
            )
        ]

    def validate(self, data):
        """Проверка, что пользователь не пытается подписаться на себя."""
        if data['user'] == data['following']:
            raise serializers.ValidationError(
                'Вы не можете подписаться на себя.'
            )
        return data

    def to_representation(self, instance):
        request = self.context.get('request')
        return UserSubscriptionsListSerializer(
            instance.following, context={'request': request}
        ).data


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор модели Ingredient."""
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class RecipeIngredientsSerializer(serializers.ModelSerializer):
    """Сериализатор модели RecipeIngredient."""
    id = serializers.PrimaryKeyRelatedField(
        source='ingredient.id', read_only=True
    )
    name = serializers.CharField(
        source='ingredient.name'
    )
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор модели Tag."""
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class RecipeReadSerializer(serializers.ModelSerializer):
    """Сериализатор модели Recipe (для GET-запросов)."""
    author = UserReadSerializer(read_only=True)
    ingredients = RecipeIngredientsSerializer(
        source='ingredient_recipe', many=True, read_only=True
    )
    tags = TagSerializer(many=True, read_only=True)
    image = Base64ImageField()
    is_favorited = serializers.SerializerMethodField('get_is_favorited',)
    is_in_shopping_cart = serializers.SerializerMethodField(
        'get_is_in_shopping_cart',
    )

    class Meta:
        model = Recipe
        fields = (
            'id', 'author', 'name', 'image', 'text', 'ingredients', 'tags',
            'cooking_time', 'is_favorited', 'is_in_shopping_cart',
        )

    def get_is_favorited(self, obj):
        """Проверяем, находится ли рецепт в избранном этого пользователя."""
        request = self.context.get('request')
        return bool(
            request and request.user.is_authenticated
            and Favorites.objects.filter(
                recipe=obj,
                user=request.user
            ).exists()
        )

    def get_is_in_shopping_cart(self, obj):
        """Проверяем, есть ли рецепт в списке покупок этого пользователя."""
        request = self.context.get('request')
        return bool(
            request and request.user.is_authenticated
            and ShoppingCart.objects.filter(
                recipe=obj,
                user=request.user
            ).exists()
        )


class IngredientAmountSerializer(serializers.ModelSerializer):
    """Сериализатор для количества ингредиента."""
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source='ingredient',
        required=True
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')


class RecipeCreateSerializer(serializers.ModelSerializer):
    """Сериализатор создания, редактирования рецепта."""
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
    )
    author = serializers.HiddenField(default=serializers.CurrentUserDefault())
    ingredients = IngredientAmountSerializer(
        many=True,
    )
    image = Base64ImageField(required=True)
    image_url = serializers.SerializerMethodField(
        'get_image_url',
        read_only=True,
    )
    short_url = serializers.CharField(read_only=True, required=False)

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'name',
            'image', 'text', 'cooking_time', 'image_url', 'short_url'
        )

    def get_image_url(self, obj):
        return obj.image.url

    def create_recipe_ingredients(self, recipe, ingredients_data):
        """Функция создает ингредиенты для рецепта."""
        objs = [
            RecipeIngredient(
                recipe=recipe,
                ingredient=ingredient_data['ingredient'],
                amount=ingredient_data['amount']
            )
            for ingredient_data in ingredients_data
        ]
        RecipeIngredient.objects.bulk_create(objs)

    @transaction.atomic
    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self.create_recipe_ingredients(recipe, ingredients_data)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        instance.tags.set(tags)
        instance.ingredient_recipe.all().delete()
        self.create_recipe_ingredients(instance, ingredients_data)
        return super().update(instance, validated_data)

    def validate(self, data):
        """Валидация данных рецепта."""
        ingredients_data = data.get('ingredients')
        tags = data.get('tags')
        if not tags:
            raise serializers.ValidationError(
                {'tags': 'Укажите тег(и).'}
            )
        if not ingredients_data:
            raise serializers.ValidationError(
                {'ingredients': 'Укажите ингредиенты.'}
            )
        if len(set(tags)) != len(tags):
            raise serializers.ValidationError(
                {'tags': 'Вы указали один и тот же тег несколько раз.'}
            )
        ingredient_id = [item['ingredient'].id for item in ingredients_data]
        if len(set(ingredient_id)) != len(ingredient_id):
            raise serializers.ValidationError({
                'ingredients': 'Вы указали повторно один и тот же ингредиент.'
            })
        return data

    def to_representation(self, instance):
        return RecipeReadSerializer(
            instance=instance,
            context=self.context
        ).data


class FavoriteShoppingCartAddSerializer(serializers.ModelSerializer):
    """Базовый сериализатор избранного и списка покупок."""
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = UserRecipeBaseModel
        fields = (
            'user', 'recipe',
        )
        abstract = True

    def to_representation(self, instance):
        recipe = instance.recipe
        return SubscribeRecipeSerializer(
            recipe,
            context=self.context
        ).data


class FavoritesSerializer(FavoriteShoppingCartAddSerializer):
    """Сериализатор избранного."""
    class Meta:
        model = Favorites
        fields = (
            'user', 'recipe',
        )
        validators = [
            UniqueTogetherValidator(
                queryset=Favorites.objects.all(),
                fields=('user', 'recipe'),
                message='Рецепт уже добавлен в избранное.'
            )
        ]


class ShoppingCartSerializer(FavoriteShoppingCartAddSerializer):
    """Сериализатор списка покупок."""
    class Meta:
        model = ShoppingCart
        fields = (
            'user', 'recipe',
        )
        validators = [
            UniqueTogetherValidator(
                queryset=ShoppingCart.objects.all(),
                fields=('user', 'recipe'),
                message='Рецепт уже добавлен в список покупок.'
            )
        ]
