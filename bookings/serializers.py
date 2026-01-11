from rest_framework import serializers
from .models import Booking


class BookingSerializer(serializers.ModelSerializer):
    tenant_email = serializers.EmailField(source='tenant.email', read_only=True)
    listing_title = serializers.CharField(source='listing.title', read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id",
            "tenant",
            "tenant_email",
            "listing",
            "listing_title",
            "start_date",
            "end_date",
            "status",
            "created_at",
            "is_active"
        ]
        read_only_fields = ["tenant", "status", "created_at", "is_active"]

    def validate(self, data):
        # Проверка что пользователь - tenant
        if self.context['request'].user.user_type != 'tenant':
            raise serializers.ValidationError("Only tenants can create bookings")

        # Проверка дат
        if data['start_date'] >= data['end_date']:
            raise serializers.ValidationError("End date must be after start date")

        # Проверка что listing активен
        listing = data['listing']
        if not listing.is_active:
            raise serializers.ValidationError("This listing is not available")

        # Проверка пересечений с существующими approved бронированиями
        overlapping_bookings = Booking.objects.filter(
            listing=listing,
            status__in=[Booking.STATUS_APPROVED, Booking.STATUS_PENDING],
            start_date__lt=data['end_date'],
            end_date__gt=data['start_date']
        )

        if overlapping_bookings.exists():
            raise serializers.ValidationError("These dates are not available")

        return data
