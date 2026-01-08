from rest_framework import viewsets, permissions, filters, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from .models import Listing
from .serializers import (
    ListingSerializer,
    ListingCreateSerializer
)
from users.permissions import IsLandlordOrReadOnly


class ListingViewSet(viewsets.ModelViewSet):
    queryset = Listing.objects.all()
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['price', 'created_at']

    permission_classes = [permissions.IsAuthenticated, IsLandlordOrReadOnly]

    http_method_names = ['get', 'post', 'put', 'patch', 'delete']

    def get_serializer_class(self):
        if self.action == 'create':
            return ListingCreateSerializer
        return ListingSerializer

    def perform_create(self, serializer):
        if self.request.user.user_type != 'landlord':
            raise PermissionDenied("Только арендодатель может создавать объявления")
        serializer.save(owner=self.request.user)

    def get_queryset(self):
        queryset = Listing.objects.filter(is_active=True)

        city = self.request.query_params.get('city')
        if city:
            queryset = queryset.filter(city__icontains=city)

        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)

        rooms = self.request.query_params.get('rooms')
        if rooms:
            queryset = queryset.filter(rooms=rooms)

        housing_type = self.request.query_params.get('housing_type')
        if housing_type:
            queryset = queryset.filter(housing_type=housing_type)

        return queryset