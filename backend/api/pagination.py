from rest_framework.pagination import PageNumberPagination

from .constants import DEFAULT_PAGES_LIMIT


class RecipesPagination(PageNumberPagination):
    page_size_query_param = 'limit'
    page_size = DEFAULT_PAGES_LIMIT
