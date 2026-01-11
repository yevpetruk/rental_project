from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Booking
from .serializers import BookingSerializer
from .permissions import IsTenant, IsLandlord


class BookingViewSet(viewsets.ModelViewSet):
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Booking.objects.select_related('listing', 'tenant', 'listing__owner')

        if user.user_type == "tenant":
            return queryset.filter(tenant=user)
        elif user.user_type == "landlord":
            return queryset.filter(listing__owner=user)
        return Booking.objects.none()

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), IsTenant()]

        if self.action in ["approve", "reject", "complete"]:
            return [IsAuthenticated(), IsLandlord()]

        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(
            tenant=self.request.user,
            status=Booking.STATUS_PENDING
        )

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        booking = self.get_object()

        if booking.listing.owner != request.user:
            return Response(
                {"detail": "You are not the owner of this listing"},
                status=status.HTTP_403_FORBIDDEN
            )

        if booking.status != Booking.STATUS_PENDING:
            return Response(
                {"detail": f"Booking is already {booking.status}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Проверяем нет ли пересечений с другими approved бронированиями
        overlapping = Booking.objects.filter(
            listing=booking.listing,
            status=Booking.STATUS_APPROVED,
            start_date__lt=booking.end_date,
            end_date__gt=booking.start_date
        ).exclude(id=booking.id)

        if overlapping.exists():
            return Response(
                {"detail": "Dates conflict with existing approved booking"},
                status=status.HTTP_400_BAD_REQUEST
            )

        booking.status = Booking.STATUS_APPROVED
        booking.save()

        return Response(
            {"detail": "Booking approved"},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Пометить бронирование как завершённое (для отзывов)"""
        booking = self.get_object()

        if booking.listing.owner != request.user:
            return Response(
                {"detail": "You are not the owner of this listing"},
                status=status.HTTP_403_FORBIDDEN
            )

        if booking.status != Booking.STATUS_APPROVED:
            return Response(
                {"detail": "Only approved bookings can be completed"},
                status=status.HTTP_400_BAD_REQUEST
            )

        from django.utils import timezone
        if booking.end_date > timezone.now().date():
            return Response(
                {"detail": "Booking end date hasn't passed yet"},
                status=status.HTTP_400_BAD_REQUEST
            )

        booking.status = Booking.STATUS_COMPLETED
        booking.save()

        return Response(
            {"detail": "Booking marked as completed"},
            status=status.HTTP_200_OK
        )
    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        booking = self.get_object()

        if booking.listing.owner != request.user:
            return Response(
                {"detail": "You are not the owner of this listing"},
                status=status.HTTP_403_FORBIDDEN
            )

        booking.status = Booking.STATUS_REJECTED
        booking.save()

        return Response(
            {"detail": "Booking rejected"},
            status=status.HTTP_200_OK
        )


    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        booking = self.get_object()

        if booking.tenant != request.user:
            return Response(
                {"detail": "You can cancel only your own booking"},
                status=status.HTTP_403_FORBIDDEN
            )

        booking.status = Booking.STATUS_CANCELED
        booking.save()

        return Response(
            {"detail": "Booking canceled"},
            status=status.HTTP_200_OK
        )