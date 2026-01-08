from rest_framework import serializers
from .models import Review
from users.serializers import UserSerializer
from listings.serializers import ListingSerializer
from bookings.models import Booking


class ReviewSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    listing = ListingSerializer(read_only=True)
    booking_id = serializers.PrimaryKeyRelatedField(
        queryset=Booking.objects.all(),
        source='booking',
        write_only=True
    )

    class Meta:
        model = Review
        fields = [
            'id', 'booking_id', 'booking', 'listing', 'author',
            'rating', 'comment', 'created_at', 'updated_at'
        ]
        read_only_fields = ['author', 'listing', 'created_at', 'updated_at']