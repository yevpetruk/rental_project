from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import User


class UserModelTest(TestCase):
    def test_create_user(self):
        """Тест создания обычного пользователя"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            user_type='tenant'
        )
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.user_type, 'tenant')
        self.assertTrue(user.check_password('testpass123'))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_superuser(self):
        """Тест создания суперпользователя"""
        admin_user = User.objects.create_superuser(
            username='adminuser',
            email='admin@example.com',
            password='adminpass123'
        )
        self.assertEqual(admin_user.username, 'adminuser')
        self.assertEqual(admin_user.email, 'admin@example.com')
        self.assertTrue(admin_user.is_active)
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)

    def test_email_unique(self):
        """Тест уникальности email"""
        User.objects.create_user(
            username='user1',
            email='duplicate@example.com',
            password='pass123'
        )
        with self.assertRaises(Exception):
            User.objects.create_user(
                username='user2',
                email='duplicate@example.com',
                password='pass456'
            )

    def test_username_unique(self):
        """Тест уникальности username"""
        User.objects.create_user(
            username='sameuser',
            email='test1@example.com',
            password='pass123'
        )
        with self.assertRaises(Exception):
            User.objects.create_user(
                username='sameuser',
                email='test2@example.com',
                password='pass456'
            )


class UserAPITest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.tenant_data = {
            'username': 'tenantuser',
            'email': 'tenant@test.com',
            'password': 'tenantpass123',
            'user_type': 'tenant'
        }
        self.landlord_data = {
            'username': 'landlorduser',
            'email': 'landlord@test.com',
            'password': 'landlordpass123',
            'user_type': 'landlord'
        }

    def test_register_tenant(self):
        """Тест регистрации арендатора"""
        url = reverse('user-register')
        response = self.client.post(url, self.tenant_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('user', response.data)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user']['user_type'], 'tenant')

        # Проверяем что пользователь создан в БД
        self.assertTrue(User.objects.filter(email='tenant@test.com').exists())

    def test_register_landlord(self):
        """Тест регистрации арендодателя"""
        url = reverse('user-register')
        response = self.client.post(url, self.landlord_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user']['user_type'], 'landlord')
        self.assertEqual(response.data['user']['username'], 'landlorduser')

    def test_register_without_username(self):
        """Тест регистрации без username"""
        url = reverse('user-register')
        data = {
            'email': 'test@example.com',
            'password': 'test123',
            'user_type': 'tenant'
        }
        response = self.client.post(url, data, format='json')
        # Должна быть ошибка, так как username обязателен
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_username(self):
        """Тест регистрации с существующим username"""
        User.objects.create_user(
            username='existinguser',
            email='existing@test.com',
            password='pass123'
        )

        url = reverse('user-register')
        data = {
            'username': 'existinguser',  # Существующий username
            'email': 'new@test.com',
            'password': 'pass456',
            'user_type': 'tenant'
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_token_with_username(self):
        """Тест получения JWT токена с username"""
        # Создаем пользователя
        User.objects.create_user(
            username='tokenuser',
            email='token@test.com',
            password='tokenpass123',
            user_type='tenant'
        )

        url = reverse('token_obtain_pair')
        # ВАЖНО: SimpleJWT по умолчанию использует username поле для аутентификации
        data = {
            'username': 'tokenuser',  # Используем username
            'password': 'tokenpass123'
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_get_token_with_email_should_fail(self):
        """Тест что получение токена с email не работает"""
        User.objects.create_user(
            username='emailuser',
            email='email@test.com',
            password='pass123'
        )

        url = reverse('token_obtain_pair')
        # Пытаемся использовать email вместо username
        data = {
            'username': 'email@test.com',  # email как username
            'password': 'pass123'
        }
        response = self.client.post(url, data, format='json')

        # Должно быть 401, так как username 'email@test.com' не существует
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_token_wrong_password(self):
        """Тест получения токена с неправильным паролем"""
        User.objects.create_user(
            username='wrongpassuser',
            email='wrong@test.com',
            password='correct123',
            user_type='tenant'
        )

        url = reverse('token_obtain_pair')
        data = {
            'username': 'wrongpassuser',
            'password': 'wrongpassword'
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_token(self):
        """Тест обновления токена"""
        # Создаем пользователя и получаем токен
        User.objects.create_user(
            username='refreshuser',
            email='refresh@test.com',
            password='pass123'
        )

        # Получаем токен
        token_url = reverse('token_obtain_pair')
        response = self.client.post(token_url, {
            'username': 'refreshuser',
            'password': 'pass123'
        }, format='json')

        refresh_token = response.data['refresh']

        # Обновляем токен
        refresh_url = reverse('token_refresh')
        response = self.client.post(refresh_url, {
            'refresh': refresh_token
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_get_user_profile_authenticated(self):
        """Тест получения профиля аутентифицированным пользователем"""
        # Создаем и аутентифицируем пользователя
        user = User.objects.create_user(
            username='profileuser',
            email='profile@test.com',
            password='pass123',
            user_type='tenant'
        )

        # Получаем токен
        token_url = reverse('token_obtain_pair')
        response = self.client.post(token_url, {
            'username': 'profileuser',
            'password': 'pass123'
        }, format='json')
        token = response.data['access']

        # Получаем профиль
        url = reverse('user-detail', args=[user.id])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'profileuser')
        self.assertEqual(response.data['email'], 'profile@test.com')

    def test_get_user_profile_unauthenticated(self):
        """Тест что нельзя получить профиль без аутентификации"""
        user = User.objects.create_user(
            username='unauthuser',
            email='unauth@test.com',
            password='pass123'
        )

        url = reverse('user-detail', args=[user.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

