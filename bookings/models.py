from django.conf import settings
from django.db import models
from listings.models import Listing


class Booking(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CANCELED = 'canceled'
    STATUS_COMPLETED = 'completed'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_CANCELED, 'Canceled'),
        (STATUS_COMPLETED, 'Completed'),
    ]

    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name='bookings'
    )
    tenant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bookings'
    )
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Booking #{self.id} - {self.listing}'

    def clean(self):
        """Валидация дат"""
        if self.start_date >= self.end_date:
            raise ValidationError('End date must be after start date')

        # Проверяем, что даты не в прошлом
        from django.utils import timezone
        if self.start_date < timezone.now().date():
            raise ValidationError('Start date cannot be in the past')

    def save(self, *args, **kwargs):
        self.full_clean()  # Вызываем валидацию при сохранении
        super().save(*args, **kwargs)

    @property
    def is_active(self):
        """Бронирование активно если approved и даты валидны"""
        from django.utils import timezone
        today = timezone.now().date()
        return (
                self.status == self.STATUS_APPROVED and
                self.start_date <= today <= self.end_date
        )