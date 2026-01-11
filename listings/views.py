from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Q

from .models import Listing, ViewHistory
from .serializers import ListingSerializer, ListingCreateSerializer
from .filters import ListingFilter
from users.permissions import IsLandlordOrReadOnly

class ListingViewSet(viewsets.ModelViewSet):
    serializer_class = ListingSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ListingFilter
    search_fields = ['title', 'description', 'location', 'city', 'district']
    ordering_fields = ['price', 'created_at', 'updated_at', 'rooms']
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsLandlordOrReadOnly]

    def get_queryset(self):
        # Базовый queryset с оптимизацией запросов
        queryset = Listing.objects.select_related('owner').prefetch_related('images')

        # Для аутентифицированных пользователей показываем все активные
        # Для неаутентифицированных - тоже все активные
        # Landlord видит и свои неактивные тоже
        if self.request.user.is_authenticated:
            if self.request.user.user_type == 'landlord':
                # Landlord видит ВСЕ свои объявления
                queryset = queryset.filter(owner=self.request.user)
            else:
                # Tenant видит все активные объявления
                queryset = queryset.filter(is_active=True)
        else:
            # Неаутентифицированные видят только активные
            queryset = queryset.filter(is_active=True)

        # Сохраняем просмотр если пользователь аутентифицирован
        if self.request.user.is_authenticated and self.action == 'retrieve':
            listing_id = self.kwargs.get('pk')
            if listing_id:
                ViewHistory.objects.get_or_create(
                    user=self.request.user,
                    listing_id=listing_id
                )

        return queryset

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ListingCreateSerializer
        return ListingSerializer

    def perform_create(self, serializer):
        if self.request.user.user_type != 'landlord':
            raise PermissionDenied("Только арендодатель может создавать объявления")
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Переключение статуса активность объявления (только для владельца)"""
        listing = self.get_object()
        if listing.owner != request.user:
            return Response(
                {'error': 'You are not the owner of this listing'},
                status=status.HTTP_403_FORBIDDEN
            )

        listing.is_active = not listing.is_active
        listing.save()

        return Response({
            'id': listing.id,
            'is_active': listing.is_active,
            'message': f'Listing is now {"active" if listing.is_active else "inactive"}'
        })

    @action(detail=False, methods=['get'])
    def popular(self, request):
        """Популярные объявления (по количеству просмотров)"""
        popular_listings = Listing.objects.filter(is_active=True).annotate(
            views_count=Count('views')
        ).order_by('-views_count')[:10]

        serializer = self.get_serializer(popular_listings, many=True)
        return Response(serializer.data)