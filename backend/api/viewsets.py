from rest_framework import mixins, viewsets
from rest_framework.permissions import AllowAny


class TagIngredientBaseViewSet(
        mixins.ListModelMixin,
        mixins.RetrieveModelMixin,
        viewsets.GenericViewSet
):
    """Базовый вьюсет для TagViewSet и IngredientViewSet."""
    permission_classes = (AllowAny,)
    ordering_fields = ('name',)
    pagination_class = None
