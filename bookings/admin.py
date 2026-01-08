from django.contrib import admin
from .models import Booking

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'listing', 'tenant', 'check_in', 'check_out', 'status', 'total_price')
    list_filter = ('status',)
    search_fields = ('listing__title', 'tenant__username')
    raw_id_fields = ('listing', 'tenant')