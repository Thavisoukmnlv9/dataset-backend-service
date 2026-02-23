# Users API Documentation

This document describes the API endpoints for managing user accounts in the dataset tourism middleware system.

## Base URL
```
/api/users
```

## Response Format
All API responses follow a standard format:

```json
{
  "success": true,
  "data": <response_data>,
  "message": "Operation successful",
  "timestamp": "2024-01-01T00:00:00.000Z",
  "request_id": "optional-request-id"
}
```

## Error Response Format
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Error description",
    "details": {}
  },
  "timestamp": "2024-01-01T00:00:00.000Z",
  "request_id": "optional-request-id"
}
```

---

## Endpoints

### 1. Create User with Form Data

Create a new user account with form data and optional image upload.

**Endpoint:** `POST /api/users/`

**Authentication:** Required

**Content-Type:** `multipart/form-data`

**Form Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `email` | string | Yes | User email address |
| `phone_number` | string | No | Phone number |
| `imageFile` | file | No | Profile image file |
| `role` | string | No | User role |
| `is_anonymous` | boolean | No | Whether user is anonymous (default: false) |
| `email_verified` | boolean | No | Whether email is verified (default: false) |
| `phone_number_verified` | boolean | No | Whether phone is verified (default: false) |
| `last_login_at` | string | No | Last login date (ISO format) |
| `login_count` | integer | No | Login count (default: 0) |
| `accounts_json` | string | No | JSON string of accounts data |
| `user_roles_json` | string | No | JSON string of user roles data |

**Example Request:**
```bash
curl -X POST "https://api.dataset.com/api/users/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "email=user@example.com" \
  -F "phone_number=+856 20 1234 5678" \
  -F "role=tourist" \
  -F "is_anonymous=false" \
  -F "email_verified=true" \
  -F "imageFile=@profile.jpg"
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com",
    "phone_number": "+856 20 1234 5678",
    "profile_image_url": "https://minio.example.com/users/profile_123.jpg",
    "role": "tourist",
    "is_anonymous": false,
    "email_verified": true,
    "phone_number_verified": false,
    "last_login_at": null,
    "login_count": 0,
    "is_active": true,
    "created_at": "2024-01-01T00:00:00.000Z",
    "updated_at": "2024-01-01T00:00:00.000Z"
  },
  "message": "User created successfully",
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

**Possible Error Responses:**
- `400 Bad Request` - Invalid input data or file upload error
- `401 Unauthorized` - Authentication required
- `409 Conflict` - Email already exists
- `422 Unprocessable Entity` - Validation errors
- `500 Internal Server Error` - Server error

---

### 2. Get Users List

Retrieve a paginated list of users with optional filtering.

**Endpoint:** `GET /api/users/`

**Authentication:** Not required

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `email` | string | No | - | Filter by email |
| `phone_number` | string | No | - | Filter by phone number |
| `role` | string | No | - | Filter by role |
| `banned` | boolean | No | - | Filter by ban status |
| `is_anonymous` | boolean | No | - | Filter by anonymous status |
| `email_verified` | boolean | No | - | Filter by email verification |
| `phone_number_verified` | boolean | No | - | Filter by phone verification |
| `created_from` | datetime | No | - | Filter by creation date from |
| `created_to` | datetime | No | - | Filter by creation date to |
| `last_login_from` | datetime | No | - | Filter by last login from |
| `last_login_to` | datetime | No | - | Filter by last login to |
| `search` | string | No | - | Search query |
| `filters` | string | No | - | JSON string of filter conditions |
| `sort` | string | No | - | JSON string of sort conditions |
| `offset` | integer | No | `0` | Number of items to skip (≥ 0) |
| `limit` | integer | No | `20` | Items per page (1-100) |

**Example Request:**
```http
GET /api/users/?role=tourist&email_verified=true&limit=10&offset=0
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "users": [
      {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "email": "user@example.com",
        "phone_number": "+856 20 1234 5678",
        "profile_image_url": "https://minio.example.com/users/profile_123.jpg",
        "role": "tourist",
        "is_anonymous": false,
        "email_verified": true,
        "phone_number_verified": false,
        "last_login_at": "2024-01-15T10:30:00.000Z",
        "login_count": 15,
        "is_active": true,
        "banned": false,
        "ban_reason": null,
        "ban_expires": null,
        "created_at": "2024-01-01T00:00:00.000Z",
        "updated_at": "2024-01-15T10:30:00.000Z"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 500,
      "pages": 25,
      "offset": 0,
      "has_next": true,
      "has_prev": false
    }
  },
  "message": "Users retrieved successfully",
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

**Possible Error Responses:**
- `400 Bad Request` - Invalid query parameters
- `422 Unprocessable Entity` - Validation errors
- `500 Internal Server Error` - Server error

---

### 3. Get Single User

Retrieve detailed information about a specific user.

**Endpoint:** `GET /api/users/{user_id}`

**Authentication:** Not required

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | UUID | Yes | Unique identifier of the user |

**Example Request:**
```http
GET /api/users/123e4567-e89b-12d3-a456-426614174000
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "email": "user@example.com",
      "phone_number": "+856 20 1234 5678",
      "profile_image_url": "https://minio.example.com/users/profile_123.jpg",
      "role": "tourist",
      "is_anonymous": false,
      "email_verified": true,
      "phone_number_verified": false,
      "last_login_at": "2024-01-15T10:30:00.000Z",
      "login_count": 15,
      "is_active": true,
      "banned": false,
      "ban_reason": null,
      "ban_expires": null,
      "created_at": "2024-01-01T00:00:00.000Z",
      "updated_at": "2024-01-15T10:30:00.000Z"
    },
    "accounts": [
      {
        "id": "456e7890-e89b-12d3-a456-426614174001",
        "user_id": "123e4567-e89b-12d3-a456-426614174000",
        "provider": "google",
        "provider_id": "google_123456789",
        "created_at": "2024-01-01T00:00:00.000Z"
      }
    ],
    "user_roles": [
      {
        "id": "789e0123-e89b-12d3-a456-426614174002",
        "user_id": "123e4567-e89b-12d3-a456-426614174000",
        "role_id": "321e6543-e89b-12d3-a456-426614174003",
        "business_id": null,
        "is_active": true,
        "created_at": "2024-01-01T00:00:00.000Z"
      }
    ]
  },
  "message": "User retrieved successfully",
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

**Possible Error Responses:**
- `404 Not Found` - User not found
- `422 Unprocessable Entity` - Invalid UUID format
- `500 Internal Server Error` - Server error

---

### 4. Update User

Update an existing user account.

**Endpoint:** `PUT /api/users/{user_id}`

**Authentication:** Required (Admin only)

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | UUID | Yes | Unique identifier of the user |

**Request Body:**
```json
{
  "phone_number": "+856 20 9876 5432",
  "role": "vendor_basic",
  "email_verified": true,
  "phone_number_verified": true
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com",
    "phone_number": "+856 20 9876 5432",
    "role": "vendor_basic",
    "email_verified": true,
    "phone_number_verified": true,
    "updated_at": "2024-01-15T10:30:00.000Z"
  },
  "message": "User updated successfully",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

**Possible Error Responses:**
- `400 Bad Request` - Invalid input data
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Admin access required
- `404 Not Found` - User not found
- `422 Unprocessable Entity` - Validation errors
- `500 Internal Server Error` - Server error

---

### 5. Ban User

Ban or unban a user account.

**Endpoint:** `PUT /api/users/{user_id}/ban`

**Authentication:** Required (Admin only)

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | UUID | Yes | Unique identifier of the user |

**Request Body:**
```json
{
  "banned": true,
  "ban_reason": "Violation of terms of service",
  "ban_expires": "2024-02-01T00:00:00.000Z"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "banned": true,
    "ban_reason": "Violation of terms of service",
    "ban_expires": "2024-02-01T00:00:00.000Z",
    "updated_at": "2024-01-15T10:30:00.000Z"
  },
  "message": "User ban status updated successfully",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

**Possible Error Responses:**
- `400 Bad Request` - Invalid input data
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Admin access required
- `404 Not Found` - User not found
- `422 Unprocessable Entity` - Validation errors
- `500 Internal Server Error` - Server error

---

### 6. Verify User Email

Verify a user's email address.

**Endpoint:** `POST /api/users/{user_id}/verify-email`

**Authentication:** Required

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | UUID | Yes | Unique identifier of the user |

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com",
    "email_verified": true,
    "verified_at": "2024-01-15T10:30:00.000Z"
  },
  "message": "Email verified successfully",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

---

### 7. Verify User Phone

Verify a user's phone number.

**Endpoint:** `POST /api/users/{user_id}/verify-phone`

**Authentication:** Required

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | UUID | Yes | Unique identifier of the user |

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "phone_number": "+856 20 1234 5678",
    "phone_number_verified": true,
    "verified_at": "2024-01-15T10:30:00.000Z"
  },
  "message": "Phone number verified successfully",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

---

### 8. Delete User

Soft delete a user account.

**Endpoint:** `DELETE /api/users/{user_id}`

**Authentication:** Required (Admin only)

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | UUID | Yes | Unique identifier of the user |

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "deleted": true,
    "deleted_at": "2024-01-15T10:30:00.000Z"
  },
  "message": "User deleted successfully",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

---

### 9. Lookup Users

Quick lookup for users with simple search.

**Endpoint:** `GET /api/users/lookup`

**Authentication:** Not required

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `q` | string | No | - | Search query |
| `limit` | integer | No | `20` | Number of items to return (1-100) |
| `skip` | integer | No | `0` | Number of items to skip (≥ 0) |

**Example Request:**
```http
GET /api/users/lookup?q=john&limit=5
```

**Example Response:**
```json
{
  "success": true,
  "data": {
    "users": [
      {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "email": "john.doe@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "role": "tourist"
      }
    ],
    "total": 1
  },
  "message": "User lookup completed",
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

---

## Data Models

### User Object

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique identifier |
| `email` | string | User email address (validated) |
| `phone_number` | string | Phone number (max 20 characters) |
| `profile_image_url` | string | Profile image URL |
| `role` | string | User role |
| `is_anonymous` | boolean | Whether user is anonymous |
| `email_verified` | boolean | Whether email is verified |
| `phone_number_verified` | boolean | Whether phone is verified |
| `last_login_at` | datetime | Last login timestamp |
| `login_count` | integer | Number of login attempts |
| `is_active` | boolean | Whether account is active |
| `banned` | boolean | Whether account is banned |
| `ban_reason` | string | Reason for ban (if banned) |
| `ban_expires` | datetime | Ban expiration date |
| `created_at` | datetime | Creation timestamp |
| `updated_at` | datetime | Last update timestamp |

### User Roles

| Role | Description |
|------|-------------|
| `tourist` | Regular tourist user |
| `vendor_basic` | Basic vendor account |
| `vendor_premium` | Premium vendor account |
| `admin` | System administrator |
| `attraction_admin` | Attraction administrator |
| `system_admin` | System administrator |
| `super_admin` | Super administrator |

### Account Object

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique identifier |
| `user_id` | UUID | Associated user ID |
| `provider` | string | OAuth provider (google, facebook, etc.) |
| `provider_id` | string | Provider-specific user ID |
| `created_at` | datetime | Creation timestamp |

### User Role Object

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique identifier |
| `user_id` | UUID | Associated user ID |
| `role_id` | UUID | Associated role ID |
| `business_id` | UUID | Associated business ID |
| `is_active` | boolean | Whether role is active |
| `created_at` | datetime | Creation timestamp |

---

## Usage Examples

### Create user with form data
```bash
curl -X POST "https://api.dataset.com/api/users/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "email=user@example.com" \
  -F "phone_number=+856 20 1234 5678" \
  -F "role=tourist" \
  -F "imageFile=@profile.jpg"
```

### Get users by role
```bash
curl -X GET "https://api.dataset.com/api/users/?role=tourist&limit=20" \
  -H "Accept: application/json"
```

### Update user
```bash
curl -X PUT "https://api.dataset.com/api/users/123e4567-e89b-12d3-a456-426614174000" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "phone_number": "+856 20 9876 5432",
    "role": "vendor_basic"
  }'
```

### Ban user
```bash
curl -X PUT "https://api.dataset.com/api/users/123e4567-e89b-12d3-a456-426614174000/ban" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "banned": true,
    "ban_reason": "Violation of terms of service"
  }'
```

### Lookup users
```bash
curl -X GET "https://api.dataset.com/api/users/lookup?q=john&limit=10" \
  -H "Accept: application/json"
```

---

## Notes

- All timestamps are in UTC format (ISO 8601)
- UUIDs are returned as strings
- Pagination uses offset-based pagination (not page-based)
- The `limit` parameter has a maximum value of 100
- All string fields have maximum length limits as specified in the data models
- Profile images are uploaded to MinIO storage
- User roles can be assigned to specific business
- Ban functionality includes expiration dates
- Email and phone verification are separate processes
- Soft delete preserves user data for audit purposes
- Admin operations require appropriate permissions
