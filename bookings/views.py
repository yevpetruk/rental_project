from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import serializers  # Импортируем serializers для ValidationError
from django.utils import timezone
from .models import Booking
from .serializers import BookingSerializer
from listings.models import Listing


class BookingViewSet(viewsets.ModelViewSet):
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Booking.objects.all()

    def get_queryset(self):
        user = self.request.user

        # Проверяем, что user имеет поле user_type
        if hasattr(user, 'user_type'):
            if user.user_type == 'landlord':
                # Арендодатель видит бронирования своих объявлений
                return Booking.objects.filter(listing__owner=user)
            else:
                # Арендатор видит только свои бронирования
                return Booking.objects.filter(tenant=user)
        return Booking.objects.none()

    def perform_create(self, serializer):
        listing = serializer.validated_data['listing']
        check_in = serializer.validated_data['check_in']
        check_out = serializer.validated_data['check_out']

        # Проверяем доступность объявления
        if not listing.is_active:
            raise serializers.ValidationError("This listing is not available")  # Теперь serializers доступен

        # Проверяем доступность дат (нет пересечений с другими бронированиями)
        overlapping_bookings = Booking.objects.filter(
            listing=listing,
            status__in=['pending', 'confirmed'],
            check_in__lt=check_out,
            check_out__gt=check_in
        )

        if overlapping_bookings.exists():
            raise serializers.ValidationError("These dates are not available")  # Теперь serializers доступен

        # Рассчитываем общую цену
        days = (check_out - check_in).days
        total_price = days * listing.price

        # Сохраняем бронирование
        serializer.save(
            tenant=self.request.user,
            status='pending',
            total_price=total_price
        )

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        # pk используется в self.get_object() для получения booking
        booking = self.get_object()

        # Только арендатор может отменить
        if booking.tenant != request.user:
            return Response(
                {'error': 'Only the tenant can cancel this booking'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Нельзя отменить подтвержденное бронирование менее чем за 2 дня
        if booking.status == 'confirmed':
            days_before = (booking.check_in - timezone.now().date()).days
            if days_before < 2:
                return Response(
                    {'error': 'Cannot cancel confirmed booking less than 2 days before check-in'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        booking.status = 'cancelled'
        booking.save()
        return Response({'status': 'Booking cancelled'})

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        # pk используется в self.get_object() для получения booking
        booking = self.get_object()

        # Только владелец объявления может подтвердить
        if booking.listing.owner != request.user:
            return Response(
                {'error': 'Only the listing owner can confirm bookings'},
                status=status.HTTP_403_FORBIDDEN
            )

        booking.status = 'confirmed'
        booking.save()
        return Response({'status': 'Booking confirmed'})