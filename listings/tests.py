from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import Listing
from users.models import User


class ListingAPITest(APITestCase):
    def setUp(self):
        self.client = APIClient()

        # Создаем тестовых пользователей с username
        self.tenant = User.objects.create_user(
            username='testtenant',
            email='tenant@test.com',
            password='tenantpass123',
            user_type='tenant'
        )

        self.landlord = User.objects.create_user(
            username='testlandlord',
            email='landlord@test.com',
            password='landlordpass123',
            user_type='landlord'
        )

        # Создаем тестовое объявление
        self.listing = Listing.objects.create(
            title='Test Listing',
            description='Test Description',
            location='Test Location',
            city='Berlin',
            district='Mitte',
            price=100.00,
            rooms=2,
            property_type='apartment',
            owner=self.landlord
        )

        # Получаем токен для landlord (используем username)
        token_url = reverse('token_obtain_pair')
        response = self.client.post(token_url, {
            'username': 'testlandlord',
            'password': 'landlordpass123'
        }, format='json')
        self.landlord_token = response.data['access']

        # Получаем токен для tenant
        response = self.client.post(token_url, {
            'username': 'testtenant',
            'password': 'tenantpass123'
        }, format='json')
        self.tenant_token = response.data['access']

    def test_create_listing_as_landlord(self):
        """Тест создания объявления арендодателем"""
        url = reverse('listing-list')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')

        data = {
            'title': 'New Listing',
            'description': 'New Description',
            'location': 'New Location',
            'city': 'Berlin',
            'district': 'Kreuzberg',
            'price': 150.50,
            'rooms': 3,
            'property_type': 'apartment',
            'is_active': True
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'New Listing')

        # Проверяем что объявление создано в БД
        self.assertTrue(Listing.objects.filter(title='New Listing').exists())

    def test_create_listing_as_tenant_forbidden(self):
        """Тест что арендатор не может создать объявление"""
        url = reverse('listing-list')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')

        data = {
            'title': 'Tenant Listing',
            'description': 'Should fail',
            'location': 'Location',
            'city': 'Berlin',
            'price': 100,
            'rooms': 2,
            'property_type': 'apartment'
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_listings_authenticated(self):
        """Тест получения списка объявлений (аутентифицированный)"""
        url = reverse('listing-list')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data['results']), 0)

    def test_get_listings_unauthenticated(self):
        """Тест получения списка объявлений (неаутентифицированный)"""
        url = reverse('listing-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Должны видеть только активные объявления
        self.assertGreater(len(response.data['results']), 0)

    def test_filter_listings_by_city(self):
        """Тест фильтрации объявлений по городу"""
        # Создаем второе объявление в другом городе
        Listing.objects.create(
            title='Hamburg Listing',
            description='In Hamburg',
            location='Hamburg Location',
            city='Hamburg',
            price=120.00,
            rooms=2,
            property_type='apartment',
            owner=self.landlord
        )

        url = reverse('listing-list') + '?city=Berlin'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Должны получить только берлинские объявления
        for listing in response.data['results']:
            self.assertEqual(listing['city'], 'Berlin')

    def test_filter_listings_by_price_range(self):
        """Тест фильтрации по диапазону цен"""
        url = reverse('listing-list') + '?min_price=50&max_price=120'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for listing in response.data['results']:
            price = float(listing['price'])
            self.assertGreaterEqual(price, 50)
            self.assertLessEqual(price, 120)

    def test_search_listings(self):
        """Тест поиска по ключевым словам"""
        url = reverse('listing-list') + '?search=Test'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data['results']), 0)

    def test_sort_listings_by_price(self):
        """Тест сортировки по цене"""
        # Создаем ещё одно объявление с другой ценой
        Listing.objects.create(
            title='Cheap Listing',
            description='Cheap',
            location='Location',
            city='Berlin',
            price=50.00,
            rooms=1,
            property_type='apartment',
            owner=self.landlord
        )

        url = reverse('listing-list') + '?ordering=price'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        prices = [float(item['price']) for item in response.data['results']]
        self.assertEqual(prices, sorted(prices))

    def test_update_listing_owner(self):
        """Тест обновления объявления владельцем"""
        url = reverse('listing-detail', args=[self.listing.id])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')

        data = {
            'title': 'Updated Title',
            'price': 120.00
        }

        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Updated Title')

        # Проверяем в БД
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.title, 'Updated Title')

    def test_update_listing_not_owner(self):
        """Тест что нельзя обновить чужое объявление"""
        # Создаем другого landlord
        other_landlord = User.objects.create_user(
            username='otherlandlord',
            email='other@test.com',
            password='otherpass123',
            user_type='landlord'
        )

        # Получаем токен для другого landlord
        token_url = reverse('token_obtain_pair')
        response = self.client.post(token_url, {
            'username': 'otherlandlord',
            'password': 'otherpass123'
        }, format='json')
        other_token = response.data['access']

        url = reverse('listing-detail', args=[self.listing.id])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {other_token}')

        response = self.client.patch(url, {'title': 'Hacked'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_listing_owner(self):
        """Тест удаления объявления владельцем"""
        url = reverse('listing-detail', args=[self.listing.id])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Проверяем что объявление удалено
        with self.assertRaises(Listing.DoesNotExist):
            Listing.objects.get(id=self.listing.id)

    def test_delete_listing_not_owner(self):
        """Тест что нельзя удалить чужое объявление"""
        url = reverse('listing-detail', args=[self.listing.id])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_toggle_listing_active(self):
        """Тест переключения активности объявления"""
        url = reverse('listing-toggle-active', args=[self.listing.id])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.landlord_token}')

        # Получаем текущий статус
        initial_active = self.listing.is_active

        # Переключаем
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['is_active'], not initial_active)

        # Обновляем из БД и проверяем
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.is_active, not initial_active)

    def test_toggle_listing_active_not_owner(self):
        """Тест что нельзя переключить активность чужого объявления"""
        url = reverse('listing-toggle-active', args=[self.listing.id])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tenant_token}')

        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_single_listing(self):
        """Тест получения одного объявления"""
        url = reverse('listing-detail', args=[self.listing.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.listing.id)
        self.assertEqual(response.data['title'], 'Test Listing')

    def test_pagination(self):
        """Тест пагинации"""
        # Создаем больше объявлений для пагинации
        for i in range(15):
            Listing.objects.create(
                title=f'Listing {i}',
                description=f'Description {i}',
                location='Location',
                city='Berlin',
                price=100 + i,
                rooms=2,
                property_type='apartment',
                owner=self.landlord
            )

        url = reverse('listing-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)

        # Проверяем размер страницы (должен быть 10 по умолчанию)
        self.assertEqual(len(response.data['results']), 10)


class ListingModelTest(TestCase):
    def setUp(self):
        self.landlord = User.objects.create_user(
            username='modellandlord',
            email='model@test.com',
            password='pass123',
            user_type='landlord'
        )

    def test_listing_str(self):
        """Тест строкового представления объявления"""
        listing = Listing.objects.create(
            title='Model Test',
            description='Test',
            location='Location',
            city='Berlin',
            price=100.00,
            rooms=2,
            property_type='house',
            owner=self.landlord
        )

        self.assertEqual(str(listing), 'Model Test (house) - 100.00€')

    def test_listing_defaults(self):
        """Тест значений по умолчанию"""
        listing = Listing.objects.create(
            title='Default Test',
            description='Test',
            location='Location',
            city='Berlin',
            price=100.00,
            rooms=2,
            property_type='apartment',
            owner=self.landlord
            # is_active не указан, должен быть True по умолчанию
        )

        self.assertTrue(listing.is_active)
        self.assertIsNotNone(listing.created_at)
        self.assertIsNotNone(listing.updated_at)

    def test_listing_inactive(self):
        """Тест создания неактивного объявления"""
        listing = Listing.objects.create(
            title='Inactive Test',
            description='Test',
            location='Location',
            city='Berlin',
            price=100.00,
            rooms=2,
            property_type='apartment',
            owner=self.landlord,
            is_active=False
        )

        self.assertFalse(listing.is_active)