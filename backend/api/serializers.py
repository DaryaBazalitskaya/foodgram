import base64

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from djoser.serializers import UserSerializer
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from recipes.models import (Favorites, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag)
from users.models import Follow

from .constants import DEFAULT_PAGES_LIMIT, MIN_VALUE

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


class CustomUserGetSerializer(serializers.ModelSerializer):
    """Сериализатор пользователя в ответ на регистрацию."""
    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name'
        )


class CustomUserCreateSerializer(serializers.ModelSerializer):
    """Сериализатор создания пользователя."""
    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name', 'password'
        )
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User(**validated_data)
        user.set_password(validated_data['password'])
        user.save()
        return user

    def to_representation(self, instance):
        return CustomUserGetSerializer(instance).data


class SubscribeRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор отображения рецептов пользователя:
    в списке рецептов автора, избранном и списке покупок."""

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class UserSubscriptionsListSerializer(UserSerializer):
    """Сериализатор пользователя для чтения."""
    avatar = Base64ImageField()
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count',
            'avatar',
        )

    def get_is_subscribed(self, obj):
        """Подписан ли текущий пользователь на автора рецепта."""
        request = self.context.get('request')
        return (
            request and request.user
            and obj.followings.filter(
                user=request.user.id
            ).exists()
        )

    def get_recipes(self, obj):
        """Список рецептов автора."""
        request = self.context.get('request')
        recipes_limit = request.GET.get('recipes_limit', DEFAULT_PAGES_LIMIT)
        try:
            recipes_limit = int(recipes_limit)
        except ValueError:
            recipes_limit = None
        recipes_list = obj.recipes.all()[:recipes_limit]
        return SubscribeRecipeSerializer(
            recipes_list,
            context=self.context,
            many=True
        ).data

    def get_recipes_count(self, user):
        """Количество рецептов автора."""
        return user.recipes.count()


class FollowSerializer(serializers.ModelSerializer):
    """Сериализатор модели Follow."""
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False
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

    def create(self, validated_data):
        """Создание подписки."""
        return Follow.objects.create(**validated_data)

    def to_representation(self, instance):
        return UserSubscriptionsListSerializer(
            instance.following, context=self.context
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
    author = UserSubscriptionsListSerializer(read_only=True)
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
            'cooking_time', 'is_favorited', 'is_in_shopping_cart', 'created_at'
        )

    def get_is_favorited(self, obj):
        """Проверяем, находится ли рецепт в избранном этого пользователя."""
        user = self.context['request'].user
        if user.is_authenticated:
            return Favorites.objects.filter(user=user, recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        """Проверяем, есть ли рецепт в списке покупок этого пользователя."""
        user = self.context['request'].user
        if user.is_authenticated:
            return ShoppingCart.objects.filter(user=user, recipe=obj).exists()


class IngredientAmountSerializer(serializers.Serializer):
    """Сериализатор количества ингредиента."""
    id = serializers.IntegerField(min_value=MIN_VALUE)
    amount = serializers.IntegerField(min_value=MIN_VALUE)


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор модели Recipe:
    создание, редактирование, удаление рецепта."""
    author = serializers.HiddenField(default=serializers.CurrentUserDefault())
    ingredients = IngredientAmountSerializer(
        many=True,
    )
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True
    )
    image = Base64ImageField()
    image_url = serializers.SerializerMethodField(
        'get_image_url',
        read_only=True,
    )

    class Meta:
        model = Recipe
        fields = (
            'id', 'name', 'author', 'text', 'image', 'tags', 'ingredients',
            'created_at', 'cooking_time', 'image_url'
        )

    def get_image_url(self, obj):
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url

    def create(self, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        for ingredient in ingredients:
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient=Ingredient.objects.get(id=ingredient['id']),
                amount=ingredient['amount']
            )
        return recipe

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.text = validated_data.get('text', instance.text)
        instance.cooking_time = validated_data.get(
            'cooking_time', instance.cooking_time
        )
        instance.image = validated_data.get('image', instance.image)
        if 'tags' in validated_data:
            tags = validated_data.pop('tags')
            instance.tags.set(tags)
        if 'ingredients' in validated_data:
            ingredients = validated_data.pop('ingredients')
            if ingredients:
                instance.ingredients.clear()
                for ingredient in ingredients:
                    RecipeIngredient.objects.create(
                        recipe=instance,
                        ingredient=Ingredient.objects.get(id=ingredient['id']),
                        amount=ingredient['amount']
                    )
        instance.save()
        return instance

    def validate_tags(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError(
                'Вы указали один и тот же тег несколько раз.'
            )
        return value

    def validate(self, data):
        if 'ingredients' not in data or (
            'ingredients' in data and not data['ingredients']
        ):
            raise serializers.ValidationError('Укажите ингредиенты.')
        if 'tags' not in data:
            raise serializers.ValidationError('Укажите тег(и).')
        tags = data['tags']
        if len(set(tags)) != len(tags):
            raise serializers.ValidationError(
                'Вы указали один и тот же тег несколько раз.'
            )
        ingredients_id = [
            ingredient.get('id') for ingredient in data.get('ingredients')
        ]
        if len(ingredients_id) != len(set(ingredients_id)):
            raise serializers.ValidationError(
                'Вы указали один и тот же ингредиент несколько раз.'
            )
        return data

    def to_representation(self, instance):
        return RecipeReadSerializer(
            instance=instance,
            context=self.context
        ).data


class FavoritesSerializer(serializers.Serializer):
    """Сериализатор избранного."""
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Favorites
        fields = (
            'user',
            'recipe',
        )


class ShoppingCartSerializer(serializers.Serializer):
    """Сериализатор списка покупок."""
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = ShoppingCart
        fields = (
            'user',
            'recipe',
        )
