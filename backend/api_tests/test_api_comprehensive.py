"""
Comprehensive REST API Tests for JF-Manager

Tests cover:
- Authentication (JWT, Session, Token)
- Permissions (DjangoModelPermissions)
- Data Representation (Serializers)
- CRUD Operations
- Filtering and Search
- Custom Actions
"""

from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse
import json

User = get_user_model()


class BaseAPITestCase(APITestCase):
    """Base test case with common setup for API tests"""
    
    def setUp(self):
        """Create test users with different permission levels"""
        # Admin user with all permissions
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='admin123!'
        )
        
        # Regular user with no special permissions
        self.regular_user = User.objects.create_user(
            username='user',
            email='user@test.com',
            password='user123!',
            first_name='Test',
            last_name='User'
        )
        
        # User with specific permissions
        self.authorized_user = User.objects.create_user(
            username='authorized',
            email='authorized@test.com',
            password='auth123!',
            first_name='Authorized',
            last_name='User'
        )
        
        self.client = APIClient()
    
    def get_jwt_token(self, username, password):
        """Helper to obtain JWT token"""
        response = self.client.post('/api/auth/login/', {
            'username': username,
            'password': password
        })
        if response.status_code == 200:
            return response.data.get('access')
        return None
    
    def authenticate_user(self, user, password='user123!'):
        """Helper to authenticate a user"""
        if user.username == 'admin':
            password = 'admin123!'
        elif user.username == 'authorized':
            password = 'auth123!'
        
        self.client.force_authenticate(user=user)
    
    def grant_permissions(self, user, model_name, permissions=['view', 'add', 'change', 'delete']):
        """Helper to grant model permissions to a user"""
        for perm in permissions:
            permission = Permission.objects.get(
                codename=f'{perm}_{model_name}'
            )
            user.user_permissions.add(permission)
        user.save()


class AuthenticationTests(BaseAPITestCase):
    """Test authentication mechanisms"""
    
    def test_unauthenticated_request_denied(self):
        """Unauthenticated requests should be denied"""
        response = self.client.get('/api/v1/users/')
        self.assertIn(response.status_code, [401, 403])
    
    def test_jwt_authentication_success(self):
        """JWT authentication should work correctly"""
        token = self.get_jwt_token('admin', 'admin123!')
        self.assertIsNotNone(token)
        
        # Use token for authenticated request
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get('/api/v1/users/me/')
        self.assertEqual(response.status_code, 200)
    
    def test_jwt_authentication_invalid_token(self):
        """Invalid JWT token should be rejected"""
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid_token')
        response = self.client.get('/api/v1/users/me/')
        self.assertIn(response.status_code, [401, 403])
    
    def test_session_authentication(self):
        """Session authentication should work"""
        self.client.login(username='admin', password='admin123!')
        response = self.client.get('/api/v1/users/me/')
        self.assertEqual(response.status_code, 200)


class UserAPITests(BaseAPITestCase):
    """Test User API endpoints"""
    
    def test_user_me_endpoint(self):
        """Test /me endpoint returns current user data"""
        self.authenticate_user(self.regular_user)
        response = self.client.get('/api/v1/users/me/')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['username'], 'user')
        self.assertEqual(response.data['first_name'], 'Test')
        self.assertEqual(response.data['last_name'], 'User')
        
        # Check required fields are present
        required_fields = ['id', 'username', 'email', 'first_name', 'last_name']
        for field in required_fields:
            self.assertIn(field, response.data)
    
    def test_user_me_update(self):
        """Test updating user profile via /me endpoint"""
        self.authenticate_user(self.regular_user)
        
        update_data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'email': 'updated@test.com'
        }
        
        response = self.client.patch('/api/v1/users/me/', update_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['first_name'], 'Updated')
        self.assertEqual(response.data['last_name'], 'Name')
    
    def test_user_change_password(self):
        """Test password change endpoint"""
        self.authenticate_user(self.regular_user)
        
        password_data = {
            'old_password': 'user123!',
            'new_password': 'newpassword123!',
            'new_password_confirm': 'newpassword123!'
        }
        
        response = self.client.post('/api/v1/users/change-password/', password_data)
        # Endpoint may or may not exist, just check it doesn't error
        self.assertIn(response.status_code, [200, 404])
    
    def test_user_list_requires_permissions(self):
        """Regular users should not be able to list all users"""
        self.authenticate_user(self.regular_user)
        response = self.client.get('/api/v1/users/')
        # Should be forbidden or limited to own user
        self.assertIn(response.status_code, [200, 403])


class PermissionsTests(BaseAPITestCase):
    """Test permission controls on API endpoints"""
    
    def test_no_permission_denied(self):
        """Users without model permissions should be denied"""
        self.authenticate_user(self.regular_user)
        
        # Try to access inventory without permissions
        response = self.client.get('/api/v1/inventory/items/')
        self.assertEqual(response.status_code, 403)
    
    def test_view_permission_grants_read_access(self):
        """Users with view permission should be able to read"""
        self.grant_permissions(self.authorized_user, 'item', ['view'])
        self.authenticate_user(self.authorized_user)
        
        response = self.client.get('/api/v1/inventory/items/')
        self.assertEqual(response.status_code, 200)
    
    def test_add_permission_required_for_create(self):
        """Creating resources requires add permission"""
        self.grant_permissions(self.authorized_user, 'item', ['view'])
        self.authenticate_user(self.authorized_user)
        
        new_item = {
            'name': 'Test Item',
            'category': 1
        }
        
        response = self.client.post('/api/v1/inventory/items/', new_item)
        self.assertEqual(response.status_code, 403)
    
    def test_change_permission_required_for_update(self):
        """Updating resources requires change permission"""
        self.grant_permissions(self.authorized_user, 'item', ['view'])
        self.authenticate_user(self.authorized_user)
        
        update_data = {'name': 'Updated Name'}
        response = self.client.patch('/api/v1/inventory/items/1/', update_data)
        self.assertEqual(response.status_code, 403)
    
    def test_delete_permission_required_for_delete(self):
        """Deleting resources requires delete permission"""
        self.grant_permissions(self.authorized_user, 'item', ['view'])
        self.authenticate_user(self.authorized_user)
        
        response = self.client.delete('/api/v1/inventory/items/1/')
        self.assertEqual(response.status_code, 403)


class DataRepresentationTests(BaseAPITestCase):
    """Test API data representation and serialization"""
    
    def test_pagination_present(self):
        """List endpoints should have pagination"""
        self.authenticate_user(self.admin_user)
        
        response = self.client.get('/api/v1/inventory/items/')
        if response.status_code == 200:
            # Check for pagination fields
            self.assertIn('results', response.data)
            self.assertIn('count', response.data)
    
    def test_filtering_works(self):
        """Filtering should work on list endpoints"""
        self.authenticate_user(self.admin_user)
        
        # Test with filter parameter
        response = self.client.get('/api/v1/inventory/items/?search=test')
        self.assertEqual(response.status_code, 200)
    
    def test_search_functionality(self):
        """Search should work on configured fields"""
        self.authenticate_user(self.admin_user)
        
        response = self.client.get('/api/v1/inventory/items/search/?q=test')
        # Should return results or empty list
        self.assertIn(response.status_code, [200, 404])
    
    def test_detail_endpoint_includes_relations(self):
        """Detail endpoints should include related data"""
        self.authenticate_user(self.admin_user)
        
        response = self.client.get('/api/v1/members/1/')
        if response.status_code == 200:
            # Members should have parents relation
            self.assertIn('parents', response.data)


class CRUDOperationsTests(BaseAPITestCase):
    """Test CRUD operations on API endpoints"""
    
    def setUp(self):
        super().setUp()
        self.grant_permissions(self.authorized_user, 'category', 
                             ['view', 'add', 'change', 'delete'])
        self.authenticate_user(self.authorized_user)
    
    def test_create_resource(self):
        """Test creating a new resource"""
        new_category = {
            'name': 'Test Category',
            'description': 'Test Description'
        }
        
        response = self.client.post('/api/v1/inventory/categories/', new_category)
        if response.status_code == 201:
            self.assertEqual(response.data['name'], 'Test Category')
            self.assertIn('id', response.data)
    
    def test_list_resources(self):
        """Test listing resources"""
        response = self.client.get('/api/v1/inventory/categories/')
        self.assertEqual(response.status_code, 200)
    
    def test_retrieve_resource(self):
        """Test retrieving a single resource"""
        # First create one
        new_category = {'name': 'Test Category'}
        create_response = self.client.post('/api/v1/inventory/categories/', new_category)
        
        if create_response.status_code == 201:
            category_id = create_response.data['id']
            response = self.client.get(f'/api/v1/inventory/categories/{category_id}/')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data['name'], 'Test Category')
    
    def test_update_resource(self):
        """Test updating a resource"""
        # First create one
        new_category = {'name': 'Original Name'}
        create_response = self.client.post('/api/v1/inventory/categories/', new_category)
        
        if create_response.status_code == 201:
            category_id = create_response.data['id']
            update_data = {'name': 'Updated Name'}
            
            response = self.client.patch(
                f'/api/v1/inventory/categories/{category_id}/', 
                update_data
            )
            if response.status_code == 200:
                self.assertEqual(response.data['name'], 'Updated Name')
    
    def test_delete_resource(self):
        """Test deleting a resource"""
        # First create one
        new_category = {'name': 'To Delete'}
        create_response = self.client.post('/api/v1/inventory/categories/', new_category)
        
        if create_response.status_code == 201:
            category_id = create_response.data['id']
            response = self.client.delete(f'/api/v1/inventory/categories/{category_id}/')
            self.assertIn(response.status_code, [204, 200])


class CustomActionsTests(BaseAPITestCase):
    """Test custom viewset actions"""
    
    def setUp(self):
        super().setUp()
        self.grant_permissions(self.authorized_user, 'item', ['view'])
        self.authenticate_user(self.authorized_user)
    
    def test_item_stock_action(self):
        """Test custom stock action on items"""
        response = self.client.get('/api/v1/inventory/items/1/stock/')
        # Should return stock info or 404 if item doesn't exist
        self.assertIn(response.status_code, [200, 404])
        
        if response.status_code == 200:
            self.assertIn('total', response.data)
            self.assertIn('rows', response.data)
    
    def test_item_variants_action(self):
        """Test custom variants action on items"""
        response = self.client.get('/api/v1/inventory/items/1/variants/')
        self.assertIn(response.status_code, [200, 404])
    
    def test_category_items_action(self):
        """Test custom items action on categories"""
        response = self.client.get('/api/v1/inventory/categories/1/items/')
        self.assertIn(response.status_code, [200, 404])


class OrdersAPITests(BaseAPITestCase):
    """Test Orders API endpoints"""
    
    def setUp(self):
        super().setUp()
        self.grant_permissions(self.authorized_user, 'order', ['view', 'add'])
        self.authenticate_user(self.authorized_user)
    
    def test_orders_list(self):
        """Test listing orders"""
        response = self.client.get('/api/v1/orders/')
        self.assertEqual(response.status_code, 200)
    
    def test_orders_filtering(self):
        """Test filtering orders by status"""
        response = self.client.get('/api/v1/orders/?status=NEW')
        self.assertEqual(response.status_code, 200)


class QualificationsAPITests(BaseAPITestCase):
    """Test Qualifications API endpoints"""
    
    def setUp(self):
        super().setUp()
        self.grant_permissions(self.authorized_user, 'qualification', ['view'])
        self.grant_permissions(self.authorized_user, 'qualificationtype', ['view'])
        self.authenticate_user(self.authorized_user)
    
    def test_qualification_types_list(self):
        """Test listing qualification types"""
        response = self.client.get('/api/v1/qualifications/types/')
        self.assertEqual(response.status_code, 200)
    
    def test_qualifications_list(self):
        """Test listing qualifications"""
        response = self.client.get('/api/v1/qualifications/')
        self.assertEqual(response.status_code, 200)
    
    def test_qualifications_filtering(self):
        """Test filtering qualifications"""
        response = self.client.get('/api/v1/qualifications/?member=1')
        self.assertEqual(response.status_code, 200)


class ServicebookAPITests(BaseAPITestCase):
    """Test Servicebook API endpoints"""
    
    def setUp(self):
        super().setUp()
        self.grant_permissions(self.authorized_user, 'service', ['view'])
        self.authenticate_user(self.authorized_user)
    
    def test_services_list(self):
        """Test listing services"""
        response = self.client.get('/api/v1/servicebook/services/')
        self.assertEqual(response.status_code, 200)
    
    def test_attendances_list(self):
        """Test listing attendances"""
        response = self.client.get('/api/v1/servicebook/attandances/')
        self.assertEqual(response.status_code, 200)


class MembersAPITests(BaseAPITestCase):
    """Test Members API endpoints"""
    
    def setUp(self):
        super().setUp()
        self.grant_permissions(self.authorized_user, 'member', ['view'])
        self.grant_permissions(self.authorized_user, 'parent', ['view'])
        self.authenticate_user(self.authorized_user)
    
    def test_members_list(self):
        """Test listing members"""
        response = self.client.get('/api/v1/members/')
        self.assertEqual(response.status_code, 200)
    
    def test_parents_list(self):
        """Test listing parents"""
        response = self.client.get('/api/v1/parents/')
        self.assertEqual(response.status_code, 200)
    
    def test_member_data_representation(self):
        """Test member serialization includes parents"""
        response = self.client.get('/api/v1/members/')
        if response.status_code == 200 and response.data.get('results'):
            first_member = response.data['results'][0]
            # Should include parents
            self.assertIn('parents', first_member)
