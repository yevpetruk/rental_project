from django.contrib import admin
from .models import Listing, ListingImage, SearchHistory, ViewHistory

@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'price', 'city', 'property_type', 'is_active')
    list_filter = ('property_type', 'city', 'is_active')
    search_fields = ('title', 'description', 'location')
    raw_id_fields = ('owner',)

@admin.register(ListingImage)
class ListingImageAdmin(admin.ModelAdmin):
    list_display = ('listing', 'image', 'is_main')
    list_filter = ('is_main',)

admin.site.register(SearchHistory)
admin.site.register(ViewHistory)