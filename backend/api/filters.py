from django_filters import rest_framework as filters

from recipes.models import Ingredient, Recipe


class IngredientFilter(filters.FilterSet):
    """Фильтр ингредиентов."""
    name = filters.CharFilter(
        lookup_expr='istartswith'
    )

    class Meta:
        model = Ingredient
        fields = ('name',)


class RecipeFilter(filters.FilterSet):
    """Фильтр рецептов."""
    author = filters.NumberFilter(field_name='author')
    tags = filters.AllValuesMultipleFilter(
        field_name='tags__slug'
    )
    is_favorited = filters.BooleanFilter(method='filter_by_is_favorite')
    is_in_shopping_cart = filters.BooleanFilter(
        method='filter_by_is_in_shopping_cart'
    )

    class Meta:
        model = Recipe
        fields = ('tags', 'author', 'is_favorited', 'is_in_shopping_cart')

    def filter_by_is_favorite(self, queryset, name, value):
        """Получаем рецепты из избранного."""
        if value and self.request.user.is_authenticated:
            return queryset.filter(
                favorites__user=self.request.user
            )
        return queryset

    def filter_by_is_in_shopping_cart(self, queryset, name, value):
        """Получаем рецепты из списка покупок."""
        if value and self.request.user.is_authenticated:
            return queryset.filter(
                shopping_cart__user=self.request.user
            )
        return queryset
