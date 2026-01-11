from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from datetime import date, timedelta
from users.models import User
from listings.models import Listing
from bookings.models import Booking
from .models import Review


class ReviewAPITest(APITestCase):
    def setUp(self):
        self.client = APIClient()

        # Создаем пользователей с username
        self.tenant = User.objects.create_user(
            username='reviewtenant',
            email='tenant@test.com',
            password='tenantpass123',
            user_type='tenant'
        )

        self.landlord = User.objects.create_user(
            username='reviewlandlord',
            email='landlord@test.com',
            password='landlordpass123',
            user_type='landlord'
        )

        # Создаем объявление
        self.listing = Listing.objects.create(
            title='Test Listing for Review',
            description='Test',
            location='Berlin',
            city='Berlin',
            price=100.00,
            rooms=2,
            property_type='apartment',
            owner=self.landlord,
            is_active=True
        )

        # Создаем завершённое бронирование
        self.booking = Booking.objects.create(
            listing=self.listing,
            tenant=self.tenant,
            start_date=date.today() - timedelta(days=10),
            end_date=date.today() - timedelta(days=3),
            status=Booking.STATUS_COMPLETED
        )

        # Создаем approved бронирование (тоже можно оставить отзыв)
        self.approved_booking = Booking.objects.create(
            listing=self.listing,
            tenant=self.tenant,
            start_date=date.today() - timedelta(days=20),
            end_date=date.today() - timedelta(days=13),
            status=Booking.STATUS_APPROVED
        )

        # Получаем токены (используем username)
        token_url = reverse('token_obtain_pair')

        response = self.client.post(token_url, {
            'username': 'reviewtenant',
            'password': 'tenantpass123'
        }, format='json')
        self.tenant_token = response.data['access']

        response = self.client.post(token_url, {
            'username': 'reviewlandlord',
            'password': 'landlordpass123'
        }, format='json')
        self.landlord_token = response.data['access']

    def test_create_review_for_completed_booking(self):
        """Тест создания отзыва для завершённого бронирования"""
        url = reverse('review-list')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')

        data = {
            'booking_id': self.booking.id,
            'rating': 5,
            'comment': 'Excellent stay!'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['rating'], 5)
        self.assertEqual(response.data['comment'], 'Excellent stay!')

        # Проверяем в БД
        review = Review.objects.get(id=response.data['id'])
        self.assertEqual(review.author, self.tenant)
        self.assertEqual(review.listing, self.listing)
        self.assertEqual(review.booking, self.booking)

    def test_create_review_for_approved_booking(self):
        """Тест создания отзыва для approved бронирования"""
        url = reverse('review-list')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')

        data = {
            'booking_id': self.approved_booking.id,
            'rating': 4,
            'comment': 'Good stay'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['rating'], 4)

    def test_create_review_for_pending_booking_forbidden(self):
        """Тест что нельзя оставить отзыв на pending бронирование"""
        # Создаем pending бронирование
        pending_booking = Booking.objects.create(
            listing=self.listing,
            tenant=self.tenant,
            start_date=date.today() - timedelta(days=5),
            end_date=date.today() - timedelta(days=2),
            status=Booking.STATUS_PENDING
        )

        url = reverse('review-list')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')

        data = {
            'booking_id': pending_booking.id,
            'rating': 3,
            'comment': 'Should fail'
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_review_not_tenant(self):
        """Тест что не-арендатор не может оставить отзыв"""
        # Создаем другого пользователя (не tenant этого бронирования)
        other_user = User.objects.create_user(
            username='otherreviewuser',
            email='other@test.com',
            password='pass123',
            user_type='tenant'
        )

        # Получаем токен другого пользователя
        token_url = reverse('token_obtain_pair')
        response = self.client.post(token_url, {
            'username': 'otherreviewuser',
            'password': 'pass123'
        }, format='json')
        other_token = response.data['access']

        url = reverse('review-list')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {other_token}')

        data = {
            'booking_id': self.booking.id,
            'rating': 1,
            'comment': 'Not my booking'
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_duplicate_review(self):
        """Тест что нельзя оставить второй отзыв на то же бронирование"""
        # Создаем первый отзыв
        Review.objects.create(
            booking=self.booking,
            listing=self.listing,
            author=self.tenant,
            rating=4,
            comment='First review'
        )

        url = reverse('review-list')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')

        data = {
            'booking_id': self.booking.id,
            'rating': 5,
            'comment': 'Second review attempt'
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rating_validation_low(self):
        """Тест валидации рейтинга (меньше 1)"""
        url = reverse('review-list')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')

        data = {
            'booking_id': self.booking.id,
            'rating': 0,
            'comment': 'Too low'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rating_validation_high(self):
        """Тест валидации рейтинга (больше 5)"""
        url = reverse('review-list')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')

        data = {
            'booking_id': self.booking.id,
            'rating': 6,
            'comment': 'Too high'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rating_validation_correct(self):
        """Тест корректного рейтинга"""
        url = reverse('review-list')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')

        data = {
            'booking_id': self.booking.id,
            'rating': 3,
            'comment': 'Good'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_get_reviews_as_tenant(self):
        """Тест получения отзывов арендатором"""
        # Создаем отзыв
        review = Review.objects.create(
            booking=self.booking,
            listing=self.listing,
            author=self.tenant,
            rating=5,
            comment='Great!'
        )

        url = reverse('review-list')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], review.id)
        self.assertEqual(response.data[0]['rating'], 5)

    def test_get_reviews_as_landlord(self):
        """Тест получения отзывов арендодателем"""
        # Создаем отзыв на объявление landlord
        review = Review.objects.create(
            booking=self.booking,
            listing=self.listing,
            author=self.tenant,
            rating=4,
            comment='Good'
        )

        # Создаем другое объявление и отзыв (не должен видеть)
        other_landlord = User.objects.create_user(
            username='otherreviewlandlord',
            email='otherlandlord@test.com',
            password='pass123',
            user_type='landlord'
        )

        other_listing = Listing.objects.create(
            title='Other Listing',
            description='Test',
            location='Berlin',
            city='Berlin',
            price=150.00,
            rooms=3,
            property_type='house',
            owner=other_landlord
        )

        other_booking = Booking.objects.create(
            listing=other_listing,
            tenant=self.tenant,
            start_date=date.today() - timedelta(days=10),
            end_date=date.today() - timedelta(days=3),
            status=Booking.STATUS_COMPLETED
        )

        Review.objects.create(
            booking=other_booking,
            listing=other_listing,
            author=self.tenant,
            rating=5,
            comment='Excellent'
        )

        url = reverse('review-list')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Landlord должен видеть только отзывы на свои объявления
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], review.id)

    def test_update_review_as_author(self):
        """Тест обновления отзыва автором"""
        # Создаем отзыв
        review = Review.objects.create(
            booking=self.booking,
            listing=self.listing,
            author=self.tenant,
            rating=3,
            comment='Average'
        )

        url = reverse('review-detail', args=[review.id])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')

        update_data = {
            'rating': 4,
            'comment': 'Actually better than average'
        }

        response = self.client.patch(url, update_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверяем в БД
        review.refresh_from_db()
        self.assertEqual(review.rating, 4)
        self.assertEqual(review.comment, 'Actually better than average')

    def test_update_review_not_author(self):
        """Тест что нельзя обновить чужой отзыв"""
        # Создаем другого пользователя
        other_user = User.objects.create_user(
            username='updatereviewuser',
            email='update@test.com',
            password='pass123',
            user_type='tenant'
        )

        # Создаем отзыв от первого пользователя
        review = Review.objects.create(
            booking=self.booking,
            listing=self.listing,
            author=self.tenant,
            rating=3,
            comment='My review'
        )

        # Получаем токен другого пользователя
        token_url = reverse('token_obtain_pair')
        response = self.client.post(token_url, {
            'username': 'updatereviewuser',
            'password': 'pass123'
        }, format='json')
        other_token = response.data['access']

        url = reverse('review-detail', args=[review.id])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {other_token}')

        response = self.client.patch(url, {'rating': 1}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_review_as_author(self):
        """Тест удаления отзыва автором"""
        review = Review.objects.create(
            booking=self.booking,
            listing=self.listing,
            author=self.tenant,
            rating=3,
            comment='To delete'
        )

        url = reverse('review-detail', args=[review.id])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Проверяем что отзыв удален
        self.assertFalse(Review.objects.filter(id=review.id).exists())

    def test_delete_review_not_author(self):
        """Тест что нельзя удалить чужой отзыв"""
        other_user = User.objects.create_user(
            username='deletereviewuser',
            email='delete@test.com',
            password='pass123',
            user_type='tenant'
        )

        review = Review.objects.create(
            booking=self.booking,
            listing=self.listing,
            author=self.tenant,
            rating=3,
            comment='Not yours'
        )

        token_url = reverse('token_obtain_pair')
        response = self.client.post(token_url, {
            'username': 'deletereviewuser',
            'password': 'pass123'
        }, format='json')
        other_token = response.data['access']

        url = reverse('review-detail', args=[review.id])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {other_token}')

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_single_review(self):
        """Тест получения одного отзыва"""
        review = Review.objects.create(
            booking=self.booking,
            listing=self.listing,
            author=self.tenant,
            rating=5,
            comment='Test review'
        )

        url = reverse('review-detail', args=[review.id])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], review.id)
        self.assertEqual(response.data['rating'], 5)
        self.assertEqual(response.data['comment'], 'Test review')

    def test_create_review_empty_comment(self):
        """Тест создания отзыва с пустым комментарием"""
        url = reverse('review-list')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')

        data = {
            'booking_id': self.booking.id,
            'rating': 4,
            'comment': ''  # Пустой комментарий
        }

        response = self.client.post(url, data, format='json')
        # Пустой комментарий допустим
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class ReviewModelTest(TestCase):
    def setUp(self):
        self.tenant = User.objects.create_user(
            username='modelreviewtenant',
            email='modeltenant@test.com',
            password='pass123',
            user_type='tenant'
        )

        self.landlord = User.objects.create_user(
            username='modelreviewlandlord',
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

        self.booking = Booking.objects.create(
            listing=self.listing,
            tenant=self.tenant,
            start_date=date.today() - timedelta(days=10),
            end_date=date.today() - timedelta(days=3),
            status=Booking.STATUS_COMPLETED
        )

    def test_review_str(self):
        """Тест строкового представления отзыва"""
        review = Review.objects.create(
            booking=self.booking,
            listing=self.listing,
            author=self.tenant,
            rating=5,
            comment='Great!'
        )

        self.assertEqual(str(review), f"Review for {self.listing.title} by {self.tenant.username}")

    def test_review_rating_validation(self):
        """Тест валидации рейтинга в модели"""
        # Корректный рейтинг
        review = Review(
            booking=self.booking,
            listing=self.listing,
            author=self.tenant,
            rating=3,
            comment='OK'
        )
        review.full_clean()  # Не должно вызывать исключение

        # Неправильный рейтинг (0)
        review.rating = 0
        with self.assertRaises(Exception):
            review.full_clean()

        # Неправильный рейтинг (6)
        review.rating = 6
        with self.assertRaises(Exception):
            review.full_clean()

    def test_review_auto_timestamps(self):
        """Тест автоматических временных меток"""
        review = Review.objects.create(
            booking=self.booking,
            listing=self.listing,
            author=self.tenant,
            rating=4,
            comment='Test'
        )

        self.assertIsNotNone(review.created_at)
        self.assertIsNotNone(review.updated_at)
        # При создании created_at и updated_at должны быть равны
        self.assertEqual(review.created_at, review.updated_at)

    def test_review_update_timestamp(self):
        """Тест обновления временной метки при изменении"""
        review = Review.objects.create(
            booking=self.booking,
            listing=self.listing,
            author=self.tenant,
            rating=4,
            comment='Test'
        )

        initial_updated = review.updated_at

        # Ждем немного и обновляем
        import time
        time.sleep(0.001)

        review.comment = 'Updated'
        review.save()

        review.refresh_from_db()
        # updated_at должен измениться
        self.assertGreater(review.updated_at, initial_updated)