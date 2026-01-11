from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from datetime import date, timedelta
from django.utils import timezone
from users.models import User
from listings.models import Listing
from .models import Booking


class BookingAPITest(APITestCase):
    def setUp(self):
        self.client = APIClient()

        # Создаем пользователей с username
        self.tenant = User.objects.create_user(
            username='bookingtenant',
            email='tenant@test.com',
            password='tenantpass123',
            user_type='tenant'
        )

        self.landlord = User.objects.create_user(
            username='bookinglandlord',
            email='landlord@test.com',
            password='landlordpass123',
            user_type='landlord'
        )

        # Создаем объявление
        self.listing = Listing.objects.create(
            title='Test Listing for Booking',
            description='Test',
            location='Berlin',
            city='Berlin',
            price=100.00,
            rooms=2,
            property_type='apartment',
            owner=self.landlord,
            is_active=True
        )

        # Даты для тестов
        self.tomorrow = date.today() + timedelta(days=1)
        self.next_week = date.today() + timedelta(days=7)

        # Получаем токены (используем username)
        token_url = reverse('token_obtain_pair')

        response = self.client.post(token_url, {
            'username': 'bookingtenant',
            'password': 'tenantpass123'
        }, format='json')
        self.tenant_token = response.data['access']

        response = self.client.post(token_url, {
            'username': 'bookinglandlord',
            'password': 'landlordpass123'
        }, format='json')
        self.landlord_token = response.data['access']

        # Создаем тестовое бронирование
        self.booking = Booking.objects.create(
            listing=self.listing,
            tenant=self.tenant,
            start_date=self.tomorrow,
            end_date=self.next_week,
            status=Booking.STATUS_PENDING
        )

    def test_create_booking_as_tenant(self):
        """Тест создания бронирования арендатором"""
        url = reverse('booking-list')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')

        # Используем другие даты
        start_date = date.today() + timedelta(days=10)
        end_date = date.today() + timedelta(days=14)

        data = {
            'listing': self.listing.id,
            'start_date': str(start_date),
            'end_date': str(end_date)
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'pending')

        # Проверяем в БД
        booking = Booking.objects.get(id=response.data['id'])
        self.assertEqual(booking.tenant, self.tenant)
        self.assertEqual(booking.listing, self.listing)

    def test_create_booking_as_landlord_forbidden(self):
        """Тест что арендодатель не может создать бронирование"""
        url = reverse('booking-list')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')

        data = {
            'listing': self.listing.id,
            'start_date': str(self.tomorrow),
            'end_date': str(self.next_week)
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_booking_past_date(self):
        """Тест бронирования с прошедшей датой"""
        url = reverse('booking-list')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')

        past_date = date.today() - timedelta(days=1)
        data = {
            'listing': self.listing.id,
            'start_date': str(past_date),
            'end_date': str(self.tomorrow)
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_booking_wrong_dates(self):
        """Тест бронирования с неправильными датами (end_date <= start_date)"""
        url = reverse('booking-list')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')

        data = {
            'listing': self.listing.id,
            'start_date': str(self.next_week),
            'end_date': str(self.tomorrow)  # end_date раньше start_date
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_booking_inactive_listing(self):
        """Тест бронирования неактивного объявления"""
        # Делаем объявление неактивным
        self.listing.is_active = False
        self.listing.save()

        url = reverse('booking-list')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')

        start_date = date.today() + timedelta(days=10)
        end_date = date.today() + timedelta(days=14)

        data = {
            'listing': self.listing.id,
            'start_date': str(start_date),
            'end_date': str(end_date)
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_booking_date_overlap(self):
        """Тест пересечения дат бронирования"""
        # Создаем approved бронирование
        Booking.objects.create(
            listing=self.listing,
            tenant=self.tenant,
            start_date=self.tomorrow,
            end_date=self.next_week,
            status=Booking.STATUS_APPROVED
        )

        # Пытаемся создать пересекающееся бронирование
        url = reverse('booking-list')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')

        overlapping_start = self.tomorrow + timedelta(days=2)
        overlapping_end = self.next_week + timedelta(days=2)

        data = {
            'listing': self.listing.id,
            'start_date': str(overlapping_start),
            'end_date': str(overlapping_end)
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_approve_booking_as_landlord(self):
        """Тест подтверждения бронирования арендодателем"""
        url = reverse('booking-approve', args=[self.booking.id])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')

        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверяем в БД
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.STATUS_APPROVED)

    def test_approve_booking_not_owner(self):
        """Тест что нельзя подтвердить бронирование не владельцем"""
        # Создаем другого landlord
        other_landlord = User.objects.create_user(
            username='otherbookinglandlord',
            email='otherlandlord@test.com',
            password='pass123',
            user_type='landlord'
        )

        # Получаем токен другого landlord
        token_url = reverse('token_obtain_pair')
        response = self.client.post(token_url, {
            'username': 'otherbookinglandlord',
            'password': 'pass123'
        }, format='json')
        other_token = response.data['access']

        url = reverse('booking-approve', args=[self.booking.id])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {other_token}')

        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_approve_already_approved_booking(self):
        """Тест что нельзя подтвердить уже подтверждённое бронирование"""
        # Меняем статус на approved
        self.booking.status = Booking.STATUS_APPROVED
        self.booking.save()

        url = reverse('booking-approve', args=[self.booking.id])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')

        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reject_booking_as_landlord(self):
        """Тест отклонения бронирования арендодателем"""
        url = reverse('booking-reject', args=[self.booking.id])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')

        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверяем в БД
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.STATUS_REJECTED)

    def test_cancel_booking_as_tenant(self):
        """Тест отмены бронирования арендатором"""
        # Меняем статус на approved для отмены
        self.booking.status = Booking.STATUS_APPROVED
        self.booking.save()

        url = reverse('booking-cancel', args=[self.booking.id])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')

        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.STATUS_CANCELED)

    def test_cancel_booking_not_tenant(self):
        """Тест что нельзя отменить чужое бронирование"""
        # Создаем другого tenant
        other_tenant = User.objects.create_user(
            username='otherbookingtenant',
            email='othertenant@test.com',
            password='pass123',
            user_type='tenant'
        )

        # Получаем токен другого tenant
        token_url = reverse('token_obtain_pair')
        response = self.client.post(token_url, {
            'username': 'otherbookingtenant',
            'password': 'pass123'
        }, format='json')
        other_token = response.data['access']

        url = reverse('booking-cancel', args=[self.booking.id])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {other_token}')

        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cancel_already_canceled_booking(self):
        """Тест что нельзя отменить уже отменённое бронирование"""
        self.booking.status = Booking.STATUS_CANCELED
        self.booking.save()

        url = reverse('booking-cancel', args=[self.booking.id])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')

        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_complete_booking_as_landlord(self):
        """Тест завершения бронирования арендодателем"""
        # Создаем бронирование в прошлом
        past_booking = Booking.objects.create(
            listing=self.listing,
            tenant=self.tenant,
            start_date=date.today() - timedelta(days=10),
            end_date=date.today() - timedelta(days=3),
            status=Booking.STATUS_APPROVED
        )

        url = reverse('booking-complete', args=[past_booking.id])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')

        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        past_booking.refresh_from_db()
        self.assertEqual(past_booking.status, Booking.STATUS_COMPLETED)

    def test_complete_booking_not_owner(self):
        """Тест что нельзя завершить бронирование не владельцем"""
        other_landlord = User.objects.create_user(
            username='completelandlord',
            email='complete@test.com',
            password='pass123',
            user_type='landlord'
        )

        token_url = reverse('token_obtain_pair')
        response = self.client.post(token_url, {
            'username': 'completelandlord',
            'password': 'pass123'
        }, format='json')
        other_token = response.data['access']

        url = reverse('booking-complete', args=[self.booking.id])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {other_token}')

        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_complete_future_booking(self):
        """Тест что нельзя завершить будущее бронирование"""
        future_booking = Booking.objects.create(
            listing=self.listing,
            tenant=self.tenant,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=17),
            status=Booking.STATUS_APPROVED
        )

        url = reverse('booking-complete', args=[future_booking.id])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')

        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_tenant_bookings(self):
        """Тест получения бронирований арендатором"""
        # Создаем ещё одно бронирование
        Booking.objects.create(
            listing=self.listing,
            tenant=self.tenant,
            start_date=self.next_week + timedelta(days=1),
            end_date=self.next_week + timedelta(days=7)
        )

        url = reverse('booking-list')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Должны видеть свои 2 бронирования
        self.assertEqual(len(response.data), 2)

    def test_get_landlord_bookings(self):
        """Тест получения бронирований арендодателем"""
        url = reverse('booking-list')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Landlord видит бронирование своего объявления
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.booking.id)

    def test_get_single_booking(self):
        """Тест получения одного бронирования"""
        url = reverse('booking-detail', args=[self.booking.id])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.booking.id)

    def test_update_booking_forbidden(self):
        """Тест что нельзя обновить бронирование (только через approve/reject/cancel)"""
        url = reverse('booking-detail', args=[self.booking.id])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')

        data = {
            'start_date': str(date.today() + timedelta(days=5))
        }

        response = self.client.patch(url, data, format='json')
        # PUT/PATCH не разрешены, только кастомные actions
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class BookingModelTest(TestCase):
    def setUp(self):
        self.tenant = User.objects.create_user(
            username='modeltenant',
            email='modeltenant@test.com',
            password='pass123',
            user_type='tenant'
        )

        self.landlord = User.objects.create_user(
            username='modellandlord',
            email='modellandlord@test.com',
            password='pass123',
            user_type='landlord'
        )

        self.listing = Listing.objects.create(
            title='Model Test Listing',
            description='Test',
            location='Berlin',
            city='Berlin',
            price=100.00,
            rooms=2,
            property_type='apartment',
            owner=self.landlord
        )

    def test_booking_str(self):
        """Тест строкового представления бронирования"""
        booking = Booking.objects.create(
            listing=self.listing,
            tenant=self.tenant,
            start_date=date.today() + timedelta(days=1),
            end_date=date.today() + timedelta(days=7)
        )

        self.assertEqual(str(booking), f'Booking #{booking.id} - {self.listing}')

    def test_booking_default_status(self):
        """Тест статуса по умолчанию"""
        booking = Booking.objects.create(
            listing=self.listing,
            tenant=self.tenant,
            start_date=date.today() + timedelta(days=1),
            end_date=date.today() + timedelta(days=7)
        )

        self.assertEqual(booking.status, Booking.STATUS_PENDING)

    def test_booking_is_active_property(self):
        """Тест свойства is_active"""
        # Approved booking covering today
        booking = Booking.objects.create(
            listing=self.listing,
            tenant=self.tenant,
            start_date=date.today() - timedelta(days=1),
            end_date=date.today() + timedelta(days=1),
            status=Booking.STATUS_APPROVED
        )

        self.assertTrue(booking.is_active)

    def test_booking_dates_validation(self):
        """Тест валидации дат бронирования"""
        # Попытка создать бронирование с end_date <= start_date
        booking = Booking(
            listing=self.listing,
            tenant=self.tenant,
            start_date=date.today() + timedelta(days=5),
            end_date=date.today() + timedelta(days=3),  # Ранее start_date
            status=Booking.STATUS_PENDING
        )

        with self.assertRaises(Exception):
            booking.full_clean()  # Должна вызвать ValidationError