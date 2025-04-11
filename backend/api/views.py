from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.serializers import UserCreateSerializer
from djoser.views import UserViewSet
from rest_framework import filters, status, viewsets
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
from .serializers import (FavoritesSerializer, FollowSerializer,
                          IngredientSerializer, RecipeCreateSerializer,
                          RecipeReadSerializer, ShoppingCartSerializer,
                          TagSerializer, UserAvatarSerializer,
                          UserListSerializer, UserReadSerializer,
                          UserSubscriptionsListSerializer)
from .viewsets import TagIngredientBaseViewSet

User = get_user_model()


class FoodgramUserViewSet(UserViewSet):
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
            return UserCreateSerializer
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

    @action(
        detail=False,
        permission_classes=(IsAuthenticated,),
    )
    def me(self, request):
        """Получение информации о текущем пользователе."""
        return super().me(request)

    @action(
        methods=('put',),
        detail=False,
        url_path='me/avatar',
        permission_classes=(IsAuthenticated,)
    )
    def update_avatar(self, request):
        user = request.user
        serializer = UserAvatarSerializer(
            user, data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        avatar_url = UserAvatarSerializer(
            user, context={'request': request}
        ).to_representation(user)
        return Response(
            {'avatar': avatar_url}, status=status.HTTP_200_OK
        )

    @update_avatar.mapping.delete
    def delete_avatar(self, request):
        user = request.user
        if not user.avatar:
            return Response(
                {'detail': 'У пользователя нет аватара.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        user.avatar.delete(save=True)
        return Response(
            data=None, status=status.HTTP_204_NO_CONTENT
        )

    @action(
        detail=False,
        permission_classes=(IsAuthenticated,),
    )
    def subscriptions(self, request):
        """Получение списка подписок пользователя."""
        paginator = self.pagination_class()
        queryset = User.objects.filter(followings__user=request.user)
        result_page = paginator.paginate_queryset(queryset, request)
        serializer = UserSubscriptionsListSerializer(
            result_page, many=True, context={'request': request}
        )
        return paginator.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=('post',),
        permission_classes=(IsAuthenticated,)
    )
    def subscribe(self, request, id=None):
        """Подписка на пользователя или отписка от него."""
        following = get_object_or_404(User, id=id)
        serializer = FollowSerializer(
            data={'user': request.user.id, 'following': following.id},
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )

    @subscribe.mapping.delete
    def delete_subscription(self, request, id=None):
        delete_number, _ = Follow.objects.filter(
            user=request.user, following=get_object_or_404(User, id=id)
        ).delete()
        if not delete_number:
            return Response(
                {'detail': 'Вы не были подписаны на этого пользователя.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            status=status.HTTP_204_NO_CONTENT
        )


class TagViewSet(TagIngredientBaseViewSet):
    """Вьюсет модели Tag."""
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ('^name',)


class IngredientViewSet(TagIngredientBaseViewSet):
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

    def get_serializer_class(self):
        """Определяем, какой из сериализаторов будет обрабатывать данные
        в зависимости от нужного действия."""
        if self.action in ('list', 'retrieve'):
            return RecipeReadSerializer
        return RecipeCreateSerializer

    @staticmethod
    def add_favorite_shopping_cart(serializer, pk, request):
        recipe = get_object_or_404(Recipe, pk=pk)
        serializer = serializer(
            data={'user': request.user.pk, 'recipe': recipe.pk},
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return serializer

    @action(
        detail=True,
        methods=('post',),
        permission_classes=(IsAuthenticated,)
    )
    def favorite(self, request, pk=None):
        """Функция добавления рецепта в избранное."""
        return Response(
            self.add_favorite_shopping_cart(
                serializer=FavoritesSerializer,
                pk=pk,
                request=request
            ).data,
            status=status.HTTP_201_CREATED
        )

    @favorite.mapping.delete
    def delete_favorite(self, request, pk=None):
        """Функция удаления рецепта из избранного."""
        delete_number, _ = Favorites.objects.filter(
            user=request.user,
            recipe=get_object_or_404(Recipe, pk=pk)
        ).delete()
        if not delete_number:
            return Response(
                {'status': 'Рецепта еще не было в избранном.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=('post',),
        permission_classes=(IsAuthenticated,)
    )
    def shopping_cart(self, request, pk=None):
        """Функция добавления рецепта в список покупок."""
        return Response(
            self.add_favorite_shopping_cart(
                serializer=ShoppingCartSerializer,
                pk=pk,
                request=request
            ).data,
            status=status.HTTP_201_CREATED
        )

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk=None):
        """Функция удаления рецепта из списка покупок."""
        delete_number, _ = ShoppingCart.objects.filter(
            user=request.user,
            recipe=get_object_or_404(Recipe, pk=pk)
        ).delete()
        if not delete_number:
            return Response(
                {'status': 'Рецепта еще не было в списке покупок.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        url_path='get-link',
        permission_classes=(AllowAny,)
    )
    def get_link(self, request, pk=None):
        """Получение короткой ссылки на рецепт."""
        recipe = self.get_object()
        short_link = request.build_absolute_uri(
            f'{settings.SITE_URL_PREFIX}r/{recipe.short_url}/'
        )
        return Response({'short-link': short_link}, status=status.HTTP_200_OK)

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
        ingredients = (
            RecipeIngredient.objects
            .filter(recipe__shopping_cart__user=request.user)
            .values('ingredient__name', 'ingredient__measurement_unit')
            .annotate(total_amount=Sum('amount'))
            .order_by('ingredient__name')
        )
        filename = 'shopping_cart.txt'
        content = ''
        for ingredient in ingredients:
            name = ingredient['ingredient__name']
            amount = ingredient['total_amount']
            unit = ingredient['ingredient__measurement_unit']
            content += f'{name}: {amount} {unit}\n'
        response = HttpResponse(
            content, content_type='text/plain; charset=utf-8'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
