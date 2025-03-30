from collections import defaultdict

import pyshorteners
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
from .permissions import IsAuthorOrReadOnly
from .serializers import (FavoritesSerializer, FollowSerializer,
                          IngredientSerializer, RecipeReadSerializer,
                          RecipeSerializer, ShoppingCartSerializer,
                          TagSerializer, UserAvatarSerializer,
                          UserSubscriptionsListSerializer)

User = get_user_model()


class CustomUserViewSet(UserViewSet):
    """Вьюсет модели пользователя и подписок."""
    serializer_class = UserSubscriptionsListSerializer

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
            serializer = UserAvatarSerializer(user, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
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

    def get_permissions(self):
        if self.action == 'me':
            return (IsAuthenticated(),)
        return super().get_permissions()

    @action(
        detail=False,
        permission_classes=(IsAuthenticated,),
    )
    def subscriptions(self, request):
        """Получение списка подписок пользователя."""
        following_users = []
        paginator = self.pagination_class()
        result_page = paginator.paginate_queryset(
            request.user.followers.all(), request
        )
        for subscription in result_page:
            following_users.append(subscription.following)
        return paginator.get_paginated_response(
            self.get_serializer(following_users, many=True).data
        )

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
                data={'user': user.id, 'following': following.id}
            )
            if serializer.is_valid():
                serializer.save()
                return Response(
                    {'detail': 'Вы успешно подписались на пользователя.'},
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
                    {'detail': 'Вы успешно отписались от пользователя.'},
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
            data = {'user': user.id, 'recipe': recipe.id}
            serializer = FavoritesSerializer(
                data=data, context={'request': request}
            )
            if serializer.is_valid():
                favorite, created = Favorites.objects.get_or_create(
                    user=user, recipe=recipe
                )
                if created:
                    return Response(
                        {'status': 'Рецепт добавлен в избранное.'},
                        status=status.HTTP_201_CREATED
                    )
                else:
                    return Response(
                        {'status': 'Вы уже добавили этот рецепт в избранное.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                return Response(
                    serializer.errors, status=status.HTTP_400_BAD_REQUEST
                )
        elif request.method == 'DELETE':
            try:
                favorite = Favorites.objects.get(user=user, recipe=recipe)
                favorite.delete()
                return Response(
                    {'status': 'Рецепт удален из избранного.'},
                    status=status.HTTP_204_NO_CONTENT
                )
            except Favorites.DoesNotExist:
                return Response(
                    {'status': 'Рецепта еще не было в избранном.'},
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
            data = {'user': user.id, 'recipe': recipe.id}
            serializer = ShoppingCartSerializer(
                data=data, context={'request': request}
            )
            if serializer.is_valid():
                shopping_cart, created = ShoppingCart.objects.get_or_create(
                    user=user, recipe=recipe
                )
                if created:
                    return Response(
                        {'status': 'Рецепт добавлен в список покупок.'},
                        status=status.HTTP_201_CREATED
                    )
                else:
                    return Response(
                        {'status': 'Вы уже добавили рецепт в список покупок.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
        elif request.method == 'DELETE':
            try:
                shopping_cart = ShoppingCart.objects.get(
                    user=user, recipe=recipe
                )
                shopping_cart.delete()
                return Response(
                    {'status': 'Рецепт удален из списка покупок.'},
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
            self.get_object().get_absolute_url()
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
