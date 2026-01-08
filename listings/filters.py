import django_filters
from .models import Listing


class ListingFilter(django_filters.FilterSet):
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr='lte')
    min_rooms = django_filters.NumberFilter(field_name="rooms", lookup_expr='gte')
    max_rooms = django_filters.NumberFilter(field_name="rooms", lookup_expr='lte')
    city = django_filters.CharFilter(field_name="city", lookup_expr='icontains')
    district = django_filters.CharFilter(field_name="district", lookup_expr='icontains')
    property_type = django_filters.CharFilter(field_name="property_type")
    is_active = django_filters.BooleanFilter(field_name="is_active")

    class Meta:
        model = Listing
        fields = ['city', 'district', 'property_type', 'is_active']