from rest_framework import serializers
from .models import Booking
from listings.serializers import ListingSerializer
from users.serializers import UserSerializer
from listings.models import Listing

class BookingSerializer(serializers.ModelSerializer):
    listing = ListingSerializer(read_only=True)
    tenant = UserSerializer(read_only=True)
    listing_id = serializers.PrimaryKeyRelatedField(
        queryset=Listing.objects.all(),
        source='listing',
        write_only=True
    )

    class Meta:
        model = Booking
        fields = [
            'id', 'listing', 'listing_id', 'tenant', 'check_in', 'check_out',
            'status', 'total_price', 'created_at', 'updated_at'
        ]
        read_only_fields = ['tenant', 'status', 'total_price', 'created_at', 'updated_at']