from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "password", "user_type", "username")
        extra_kwargs = {
            "password": {"write_only": True},
            "email": {"required": True}
        }

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Пользователь с таким email уже существует")
        return value

    def create(self, validated_data):
        username = validated_data.get("username")
        email = validated_data["email"]
        password = validated_data["password"]
        user_type = validated_data.get("user_type")

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            user_type=user_type
        )
        return user