# REST API Testing Guide

## Overview

This directory contains comprehensive tests for the JF-Manager REST API. The tests ensure:
- ✅ Proper authentication mechanisms (JWT, Session, Token)
- ✅ Permission-based access control
- ✅ Data representation and serialization
- ✅ CRUD operations
- ✅ Filtering and search functionality
- ✅ Custom actions on ViewSets

## Running Tests

### Run All API Tests

```bash
python manage.py test api_tests
```

### Run Specific Test Classes

```bash
# Authentication tests only
python manage.py test api_tests.test_api_comprehensive.AuthenticationTests

# Permission tests only
python manage.py test api_tests.test_api_comprehensive.PermissionsTests

# User API tests
python manage.py test api_tests.test_api_comprehensive.UserAPITests

# Inventory API tests
python manage.py test api_tests.test_api_comprehensive.CRUDOperationsTests
```

### Run with Verbose Output

```bash
python manage.py test api_tests --verbosity=2
```

### Run with Coverage

```bash
# Install coverage first
pip install coverage

# Run tests with coverage
coverage run --source='.' manage.py test api_tests
coverage report
coverage html  # Generate HTML report
```

## Test Structure

```
api_tests/
├── __init__.py
├── test_api_comprehensive.py  # Main API test suite
└── README.md                  # This file
```

### Test Classes

#### `BaseAPITestCase`
Base class for all API tests with common setup:
- Creates test users (admin, regular, authorized)
- Helper methods for authentication
- Permission granting utilities

#### `AuthenticationTests`
Tests authentication mechanisms:
- JWT token authentication
- Session authentication
- Invalid token rejection
- Unauthenticated access denial

#### `UserAPITests`
Tests user-related endpoints:
- `/api/v1/users/me/` - Get/update current user
- Password change functionality
- User list permissions

#### `PermissionsTests`
Tests Django model permissions:
- View permission for read access
- Add permission for create operations
- Change permission for update operations
- Delete permission for delete operations

#### `DataRepresentationTests`
Tests API data serialization:
- Pagination structure
- Filtering functionality
- Search capabilities
- Related data inclusion

#### `CRUDOperationsTests`
Tests basic CRUD operations:
- Create resources
- List resources
- Retrieve single resource
- Update resources (PATCH)
- Delete resources

#### `CustomActionsTests`
Tests custom ViewSet actions:
- Item stock action
- Item variants action
- Category items action

#### `OrdersAPITests`
Tests order management endpoints

#### `QualificationsAPITests`
Tests qualification and special task endpoints

#### `ServicebookAPITests`
Tests servicebook and attendance endpoints

#### `MembersAPITests`
Tests member and parent endpoints

## Adding New Tests

### 1. Create Test Method

```python
class MyNewAPITests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        # Grant necessary permissions
        self.grant_permissions(self.authorized_user, 'modelname', ['view', 'add'])
        self.authenticate_user(self.authorized_user)
    
    def test_my_endpoint(self):
        """Test description"""
        response = self.client.get('/api/v1/myendpoint/')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('expected_field', response.data)
```

### 2. Test Permissions

Always test both allowed and denied scenarios:

```python
def test_without_permission_denied(self):
    self.authenticate_user(self.regular_user)  # No permissions
    response = self.client.get('/api/v1/protected/')
    self.assertEqual(response.status_code, 403)

def test_with_permission_allowed(self):
    self.grant_permissions(self.authorized_user, 'model', ['view'])
    self.authenticate_user(self.authorized_user)
    response = self.client.get('/api/v1/protected/')
    self.assertEqual(response.status_code, 200)
```

### 3. Test Data Validation

```python
def test_create_with_invalid_data(self):
    invalid_data = {'field': 'invalid_value'}
    response = self.client.post('/api/v1/resource/', invalid_data)
    
    self.assertEqual(response.status_code, 400)
    self.assertIn('field', response.data)
```

## Best Practices

### 1. Use Descriptive Test Names

```python
# Good
def test_user_cannot_delete_without_delete_permission(self):
    ...

# Bad
def test_delete(self):
    ...
```

### 2. Test Edge Cases

```python
def test_pagination_last_page(self):
    """Test that last page works correctly"""
    ...

def test_search_with_special_characters(self):
    """Test search handles special characters"""
    ...
```

### 3. Clean Up After Tests

```python
def tearDown(self):
    # Clean up any resources created during test
    super().tearDown()
```

### 4. Use Assertions Effectively

```python
# Check response status
self.assertEqual(response.status_code, 200)
self.assertIn(response.status_code, [200, 201])

# Check response data
self.assertIn('key', response.data)
self.assertEqual(response.data['key'], 'value')
self.assertIsNotNone(response.data.get('key'))

# Check counts
self.assertGreaterEqual(len(response.data['results']), 1)
```

## Continuous Integration

These tests should be run as part of CI/CD pipeline:

### GitHub Actions Example

```yaml
name: API Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.11
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Run API tests
      run: |
        python manage.py test api_tests --verbosity=2
```

## Troubleshooting

### Tests Fail with "Permission Denied"

Make sure you're granting the correct permissions:

```python
self.grant_permissions(self.authorized_user, 'item', ['view', 'add', 'change', 'delete'])
```

The model name should be lowercase singular (e.g., `'item'`, not `'Item'` or `'items'`).

### Tests Fail with "Authentication Required"

Make sure you're authenticating the user before making requests:

```python
self.authenticate_user(self.authorized_user)
response = self.client.get('/api/v1/endpoint/')
```

### Tests Create Database Conflicts

Tests use a separate test database. If you're having issues:

```bash
# Clear test database
python manage.py flush --database=test
```

### Import Errors

Make sure the `api_tests` directory is in your Python path. The `__init__.py` file should exist.

## Coverage Goals

Aim for:
- **>90%** coverage for ViewSets
- **>85%** coverage for serializers
- **100%** coverage for authentication logic
- **>80%** overall API coverage

Check current coverage:

```bash
coverage report --include="*/api/*,*/views.py,*/serializers.py"
```

## Related Documentation

- [API Documentation](../API_DOCUMENTATION_ENHANCED.md) - Full API reference
- [API Quick Reference](../API_QUICK_REFERENCE.md) - Quick command reference
- [Django REST Framework Testing](https://www.django-rest-framework.org/api-guide/testing/) - Official DRF testing guide

## Contributing

When adding new API endpoints:
1. Write tests first (TDD approach)
2. Ensure all CRUD operations are tested
3. Test permission boundaries
4. Test data validation
5. Update API documentation
6. Run full test suite before committing

## Questions?

If you have questions about the tests or find issues, please:
1. Check existing tests for examples
2. Review the API documentation
3. Create an issue on GitHub
4. Ask the team in the development chat
