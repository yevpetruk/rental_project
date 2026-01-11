# 🏠 Rental Housing Platform - Backend API

A full-featured Django REST Framework backend for a rental housing marketplace platform. This system allows landlords to list properties and tenants to book them with integrated user authentication, booking management, and review systems.

## ✨ Features

### 🔐 **Authentication & Authorization**
- JWT-based authentication (access & refresh tokens)
- User roles: Tenant & Landlord
- Secure password handling with hashing
- Token blacklisting for logout functionality

### 🏠 **Listings Management**
- CRUD operations for property listings
- Advanced filtering by price, location, rooms, property type
- Full-text search in titles and descriptions
- Image upload support for properties
- Toggle listing availability

### 📅 **Booking System**
- Create, approve, reject, and cancel bookings
- Date conflict validation
- Booking status tracking (pending/approved/rejected/canceled/completed)
- Tenant and landlord-specific booking views

### ⭐ **Reviews & Ratings**
- Leave reviews for completed bookings
- Rating system (1-5 stars)
- Review validation (only tenants who booked can review)
- Prevent duplicate reviews

### 📊 **Analytics & History**
- Search history tracking
- Property view history
- Popular listings based on views
- Popular search queries

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- MySQL 5.7+/8.0
- Docker & Docker Compose (optional)

### Local Development Setup

1. **Clone the repository**
```bash
git clone https://github.com/YOUR_USERNAME/rental-project.git
cd rental-project
```
2. **Set up virtual environment**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```
3. **Install dependencies**
```bash
pip install -r requirements.txt
```
4. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your settings
```
5. **Run migrations**
```bash
python manage.py migrate
```
6. **Create superuser**
```bash
python manage.py createsuperuser
```
7. **Run development server**
```bash
python manage.py runserver
```

## 📁 **Project Structure**
```bash
rental_project/
├── users/           # User authentication & profiles
├── listings/        # Property listings
├── bookings/        # Booking management
├── reviews/         # Reviews & ratings
├── rental_project/  # Project configuration
├── tests/           # Test suites
├── nginx/           # Nginx configuration
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## 🔧 **API Endpoints**
### Authentication
POST /users/users/register/ - User registration

POST /users/token/ - Get JWT tokens

POST /users/token/refresh/ - Refresh access token

POST /users/logout/ - Logout (blacklist token)

### Listings
GET /listings/ - List all active listings

POST /listings/ - Create new listing (Landlord only)

GET /listings/{id}/ - Get specific listing

PUT/PATCH /listings/{id}/ - Update listing (Owner only)

DELETE /listings/{id}/ - Delete listing (Owner only)

POST /listings/{id}/toggle_active/ - Toggle listing status

### Bookings
GET /bookings/bookings/ - Get user's bookings

POST /bookings/bookings/ - Create booking (Tenant only)

POST /bookings/bookings/{id}/approve/ - Approve booking (Landlord)

POST /bookings/bookings/{id}/reject/ - Reject booking (Landlord)

POST /bookings/bookings/{id}/cancel/ - Cancel booking (Tenant)

POST /bookings/bookings/{id}/complete/ - Mark as completed

### Reviews
GET /reviews/reviews/ - Get reviews

POST /reviews/reviews/ - Create review (Tenant only)

PUT/PATCH /reviews/reviews/{id}/ - Update review (Author only)

DELETE /reviews/reviews/{id}/ - Delete review (Author only)

## 🔒 Security Features
- JWT authentication with refresh token rotation

- Password hashing with Django's PBKDF2

- SQL injection prevention via Django ORM

- XSS protection with template auto-escaping

- CSRF protection for session-based auth

- Rate limiting capabilities

- Secure headers middleware

- Environment-based configuration

## 📊 Database Schema
### Key Models
- User: Custom user model with tenant/landlord roles

- Listing: Property details, price, location, type

- Booking: Reservation dates, status, tenant-landlord relation

- Review: Ratings and comments for completed bookings

- SearchHistory: Track user search queries

- ViewHistory: Track property views


## 🚀 Deployment
### Production Considerations
1. Set DEBUG=False in environment

2. Configure proper ALLOWED_HOSTS

3. Use production database (consider PostgreSQL)

4. Set up SSL/TLS certificates

5. Configure email backend

6. Set up monitoring and logging

7. Implement backup strategy


## Environment Variables
### Required
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DB_NAME=rental_prod
DB_USER=rental_user
DB_PASSWORD=strong-password

### Optional
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

## 📝 License
This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments
Django & Django REST Framework teams

JWT implementation by Simple JWT

Docker community for containerization tools

All contributors and testers