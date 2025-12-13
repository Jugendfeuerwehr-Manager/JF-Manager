# API Swagger Documentation

The JF-Manager backend now includes interactive API documentation using drf-spectacular.

## Available Documentation Endpoints

Once the Django server is running, you can access the following documentation endpoints:

### 🚀 Swagger UI (Recommended)
**URL:** `http://localhost:8000/api/docs/`

An interactive API documentation interface where you can:
- Browse all available API endpoints
- View request/response schemas
- Test API calls directly from the browser
- Authenticate using JWT tokens or session authentication
- Filter and search through endpoints

### 📚 ReDoc
**URL:** `http://localhost:8000/api/redoc/`

A clean, responsive documentation interface that provides:
- Three-panel layout for easy navigation
- Detailed endpoint descriptions
- Request/response examples
- Schema definitions

### 📄 OpenAPI Schema (JSON)
**URL:** `http://localhost:8000/api/schema/`

The raw OpenAPI 3.0 schema in JSON format. Useful for:
- Generating client SDKs
- Importing into API testing tools (Postman, Insomnia)
- Integration with other tools

## Features

### Authentication Support
The documentation supports all authentication methods configured in the API:
- **JWT Authentication** (Bearer token)
- **Token Authentication** (Token-based)
- **Session Authentication** (Cookie-based)

### Interactive Testing
In Swagger UI, you can:
1. Click on any endpoint to expand it
2. Click "Try it out" button
3. Fill in parameters
4. Click "Execute" to make a real API call
5. View the response

### Authorization in Swagger UI
To test authenticated endpoints:

1. **Using JWT (Recommended):**
   - First, call the `/api/v1/auth/login/` endpoint with your credentials
   - Copy the `access` token from the response
   - Click the "Authorize" button at the top
   - Enter: `Bearer <your-access-token>`
   - Click "Authorize" and then "Close"

2. **Using Token Authentication:**
   - Obtain your token from `/api-token-auth/`
   - Click "Authorize" button
   - Enter: `Token <your-token>`

3. **Using Session Authentication:**
   - You'll be automatically authenticated if you're logged in to the Django admin

## Configuration

The API documentation is configured in `backend/jf_manager_backend/settings.py`:

```python
SPECTACULAR_SETTINGS = {
    'TITLE': 'JF-Manager API',
    'DESCRIPTION': 'API documentation for the Jugendfeuerwehr Manager',
    'VERSION': '1.0.0',
    'SCHEMA_PATH_PREFIX': '/api/v1/',
    'COMPONENT_SPLIT_REQUEST': True,
    # ... additional settings
}
```

## Customization

### Adding Descriptions to Endpoints

You can enhance the documentation by adding docstrings to your views and serializers:

```python
from drf_spectacular.utils import extend_schema, OpenApiParameter

class MemberViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing fire brigade members.
    
    Provides CRUD operations for member management including:
    - List all members
    - Create new members
    - Retrieve member details
    - Update member information
    - Delete members
    """
    
    @extend_schema(
        summary="List all members",
        description="Returns a paginated list of all fire brigade members",
        parameters=[
            OpenApiParameter(
                name='search',
                description='Search members by name',
                required=False,
                type=str
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
```

### Adding Tags

Group related endpoints together:

```python
@extend_schema(tags=['Members'])
class MemberViewSet(viewsets.ModelViewSet):
    # ...
```

## Troubleshooting

### Documentation Not Showing Endpoints

If some endpoints are missing:
1. Make sure they're using DRF's APIView, ViewSet, or Generic views
2. Check that `DEFAULT_SCHEMA_CLASS` is set correctly in settings
3. Restart the Django development server

### Authentication Not Working

Make sure you've included the authentication type prefix:
- JWT: `Bearer <token>`
- Token: `Token <token>`

### Schema Generation Errors

Run the schema generation manually to see errors:
```bash
python manage.py spectacular --color --file schema.yml
```

## Links

- [drf-spectacular Documentation](https://drf-spectacular.readthedocs.io/)
- [OpenAPI Specification](https://swagger.io/specification/)
- [Swagger UI Documentation](https://swagger.io/tools/swagger-ui/)
