from collections import defaultdict

import pyshorteners
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import (AllowAny, IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response

from recipes.models import (Favorites, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag)
from users.models import Follow

from .filters import IngredientFilter, RecipeFilter
from .pagination import RecipesPagination
from .permissions import IsAuthorOrReadOnly
from .serializers import (CustomUserCreateSerializer, FollowSerializer,
                          IngredientSerializer, RecipeReadSerializer,
                          RecipeSerializer, SubscribeRecipeSerializer,
                          TagSerializer, UserAvatarSerializer,
                          UserListSerializer, UserReadSerializer,
                          UserSubscriptionsListSerializer)

User = get_user_model()


class CustomUserViewSet(UserViewSet):
    """Вьюсет модели пользователя и подписок."""
    pagination_class = RecipesPagination

    def get_serializer_class(self):
        """Определяем, какой сериализатор использовать
        в зависимости от действия и basename."""
        if self.basename == 'users' and (
            self.action == 'retrieve' or self.action == 'me'
        ):
            return UserReadSerializer
        elif self.basename == 'users' and self.action == 'list':
            return UserListSerializer
        elif self.basename == 'users' and self.action == 'create':
            return CustomUserCreateSerializer
        return super().get_serializer_class()

    def get_serializer_context(self):
        """Добавляем request в контекст сериализатора (только для чтения)
        и проверяем basename."""
        context = super().get_serializer_context()
        if self.basename == 'users' and (
            self.action == 'retrieve' or self.action == 'me'
            or self.action == 'list'
        ):
            context['request'] = self.request
        return context

    def list(self, request):
        """Получение списка пользователей."""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = UserListSerializer(
                page, many=True, context={'request': request}
            )
            return self.get_paginated_response(serializer.data)
        serializer = UserListSerializer(
            queryset, many=True, context={'request': request}
        )
        return Response(serializer.data)

    @action(
        detail=False,
        permission_classes=(IsAuthenticated,),
    )
    def me(self, request):
        """Получение информации о текущем пользователе."""
        serializer = UserReadSerializer(
            request.user, context={'request': request}
        )
        return Response(serializer.data)

    @action(
        methods=('put', 'delete'),
        detail=False,
        url_path='me/avatar',
        permission_classes=(IsAuthenticated,)
    )
    def update_delete_avatar(self, request):
        """Обновление или удаление аватара текущего пользователя."""
        user = request.user
        if request.method == 'PUT':
            serializer = UserAvatarSerializer(
                user, data=request.data, context={'request': request}
            )
            if serializer.is_valid():
                serializer.save()
                avatar_url = UserAvatarSerializer(
                    user, context={'request': request}
                ).to_representation(user)
                return Response(
                    {'avatar': avatar_url}, status=status.HTTP_200_OK
                )
            else:
                return Response(
                    serializer.errors, status=status.HTTP_400_BAD_REQUEST
                )
        elif request.method == 'DELETE':
            if user.avatar:
                user.avatar.delete()
                user.avatar = None
                user.save()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(
                    {'detail': 'У пользователя нет аватара.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

    @action(
        detail=False,
        permission_classes=(IsAuthenticated,),
    )
    def subscriptions(self, request):
        """Получение списка подписок пользователя."""
        paginator = self.pagination_class()
        subscriptions = request.user.followers.all()
        followings = [subscription.following for subscription in subscriptions]
        result_page = paginator.paginate_queryset(
            followings, request
        )
        serializer = UserSubscriptionsListSerializer(
            result_page, many=True, context={'request': request}
        )
        return paginator.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=(IsAuthenticated,)
    )
    def subscribe(self, request, id=None):
        """Подписка на пользователя или отписка от него."""
        following = get_object_or_404(User, id=id)
        user = request.user
        if request.method == 'POST':
            serializer = FollowSerializer(
                data={'user': user.id, 'following': following.id},
                context={'request': request}
            )
            if serializer.is_valid():
                serializer.save()
                return Response(
                    serializer.data,
                    status=status.HTTP_201_CREATED
                )
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )
        elif request.method == 'DELETE':
            subscription = Follow.objects.filter(
                user=user, following=following
            ).first()
            if subscription:
                subscription.delete()
                return Response(
                    status=status.HTTP_204_NO_CONTENT
                )
            return Response(
                {'detail': 'Вы не были подписаны на этого пользователя.'},
                status=status.HTTP_400_BAD_REQUEST
            )


class BaseViewSet(
        mixins.ListModelMixin,
        mixins.RetrieveModelMixin,
        viewsets.GenericViewSet
):
    """Базовый вьюсет для TagViewSet и IngredientViewSet."""
    permission_classes = (AllowAny,)
    ordering_fields = ('name',)
    pagination_class = None


class TagViewSet(BaseViewSet):
    """Вьюсет модели Tag."""
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ('^name',)


class IngredientViewSet(BaseViewSet):
    """Вьюсет модели Ingredient."""
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filterset_class = IngredientFilter
    filter_backends = (DjangoFilterBackend,)


class RecipeViewSet(viewsets.ModelViewSet):
    """Вьюсет модели Recipe."""
    queryset = Recipe.objects.all()
    permission_classes = (IsAuthorOrReadOnly, IsAuthenticatedOrReadOnly)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    pagination_class = RecipesPagination

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_serializer_class(self):
        """Определяем, какой из сериализаторов будет обрабатывать данные
        в зависимости от нужного действия."""
        if self.action in ('list', 'retrieve'):
            return RecipeReadSerializer
        return RecipeSerializer

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=(IsAuthenticated,)
    )
    def favorite(self, request, pk=None):
        """Функция добавления/удаления рецепта из избранного."""
        recipe = get_object_or_404(Recipe, pk=pk)
        user = request.user
        if request.method == 'POST':
            favorite, created = Favorites.objects.get_or_create(
                user=user, recipe=recipe
            )
            if created:
                serializer = SubscribeRecipeSerializer(
                    recipe, context={'request': request}
                )
                return Response(
                    serializer.data,
                    status=status.HTTP_201_CREATED
                )
            else:
                return Response(
                    {'status': 'Вы уже добавили этот рецепт в избранное.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        elif request.method == 'DELETE':
            try:
                favorite = Favorites.objects.get(user=user, recipe=recipe)
                favorite.delete()
                return Response(
                    status=status.HTTP_204_NO_CONTENT
                )
            except Favorites.DoesNotExist:
                return Response(
                    status=status.HTTP_400_BAD_REQUEST
                )

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=(IsAuthenticated,)
    )
    def shopping_cart(self, request, pk=None):
        """Функция добавления/удаления рецепта из списка покупок."""
        recipe = get_object_or_404(Recipe, pk=pk)
        user = request.user
        if request.method == 'POST':
            shopping_cart, created = ShoppingCart.objects.get_or_create(
                user=user, recipe=recipe
            )
            if created:
                serializer = SubscribeRecipeSerializer(
                    recipe, context={'request': request}
                )
                return Response(
                    serializer.data,
                    status=status.HTTP_201_CREATED
                )
            else:
                return Response(
                    status=status.HTTP_400_BAD_REQUEST
                )
        elif request.method == 'DELETE':
            try:
                shopping_cart = ShoppingCart.objects.get(
                    user=user, recipe=recipe
                )
                shopping_cart.delete()
                return Response(
                    status=status.HTTP_204_NO_CONTENT
                )
            except ShoppingCart.DoesNotExist:
                return Response(
                    {'status': 'Рецепта еще не было в списке покупок.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

    @action(
        detail=True,
        url_path='get-link',
        permission_classes=(AllowAny,)
    )
    def get_link(self, request, pk=None):
        """Получение короткой ссылки на рецепт."""
        long_url = request.build_absolute_uri(
            settings.API_URL_PREFIX + f'recipes/{self.get_object().pk}/'
        )
        try:
            # Используем tinyurl для создания короткой ссылки.
            # Если вдруг этот сервис для сокращения ссылок накроется,
            # можно использовать аналоги: bit.ly или ow.ly.
            short_url = pyshorteners.Shortener().tinyurl.short(long_url)
        except Exception as e:
            return Response(
                {'error': f'Не удалось создать короткую ссылку: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        return Response({'short-link': short_url}, status=status.HTTP_200_OK)

    @action(
        detail=False,
        permission_classes=[IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        """Получение списка ингредиентов из списка покупок пользователя."""
        shopping_cart_items = ShoppingCart.objects.filter(user=request.user)
        if not shopping_cart_items.exists():
            return Response(
                {'message': 'В списке покупок нет рецептов.'},
                status=status.HTTP_204_NO_CONTENT
            )
        recipes = [item.recipe for item in shopping_cart_items]
        ingredients = defaultdict(int)
        measurement_units = {}
        for recipe in recipes:
            recipe_ingredients = RecipeIngredient.objects.filter(recipe=recipe)
            for recipe_ingredient in recipe_ingredients:
                ingredient_name = recipe_ingredient.ingredient.name
                amount = recipe_ingredient.amount
                measurement_unit = (
                    recipe_ingredient.ingredient.measurement_unit
                )
                ingredients[ingredient_name] += amount
                measurement_units[ingredient_name] = measurement_unit
        filename = 'shopping_cart.txt'
        content = ''
        for ingredient, amount in ingredients.items():
            measurement_unit = measurement_units[ingredient]
            content += f'{ingredient}: {amount} {measurement_unit}\n'
        response = HttpResponse(
            content, content_type='text/plain; charset=utf-8'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
