from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from .models import Review
from .serializers import ReviewSerializer
from bookings.models import Booking


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Review.objects.all()

    def get_queryset(self):
        user = self.request.user

        if not hasattr(user, 'user_type'):
            return Review.objects.none()

        if user.user_type == 'landlord':
            # Арендодатель видит отзывы на свои объявления
            return Review.objects.filter(listing__owner=user)
        else:
            # Арендатор видит только свои отзывы
            return Review.objects.filter(author=user)

    def perform_create(self, serializer):
        booking = serializer.validated_data['booking']

        # Проверяем, что бронирование завершено
        if booking.status != 'completed':
            return Response(
                {'error': 'Can only review completed bookings'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Проверяем, что пользователь — арендатор в этом бронировании
        if booking.tenant != self.request.user:
            return Response(
                {'error': 'You can only review your own bookings'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Проверяем, что отзыв на это бронирование ещё не оставлен
        if Review.objects.filter(booking=booking).exists():
            return Response(
                {'error': 'Review for this booking already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer.save(
            author=self.request.user,
            listing=booking.listing
        )