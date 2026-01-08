from django.contrib import admin
from .models import Review

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('listing', 'author', 'rating', 'created_at')
    list_filter = ('rating',)
    search_fields = ('listing__title', 'author__username')
    raw_id_fields = ('listing', 'author', 'booking')