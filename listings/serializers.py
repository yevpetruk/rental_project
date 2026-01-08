from rest_framework import serializers
from .models import Listing


class ListingSerializer(serializers.ModelSerializer):
    owner = serializers.StringRelatedField()

    class Meta:
        model = Listing
        fields = '__all__'


class ListingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Listing
        exclude = ('owner', 'created_at', 'updated_at')