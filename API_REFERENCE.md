# API Reference - Multi-Competition Voting System

## Authentication

### POST /register
Register a new user.

**Request:**
```html
Form Data:
- username (string, min 3 chars) - Unique username
- email (string) - User email address
- password (string, min 6 chars) - Password
- confirm_password (string) - Must match password
```

**Response:**
- Success (200): Redirect to /competitions with auth_token cookie
- Error: Return register page with error message

**Example:**
```bash
curl -X POST http://localhost:8080/register \
  -F "username=newuser" \
  -F "email=user@example.com" \
  -F "password=pass123" \
  -F "confirm_password=pass123"
```

---

### POST /login
Login with existing credentials.

**Request:**
```html
Form Data:
- username (string)
- password (string)
```

**Response:**
- Success (200): Redirect to /competitions with auth_token cookie
- Error: Return login page with error message

**Example:**
```bash
curl -X POST http://localhost:8080/login \
  -F "username=admin" \
  -F "password=admin123"
```

---

### GET /logout
Logout and clear session.

**Response:**
- Success (200): Redirect to /login, clear auth_token cookie

**Example:**
```bash
curl http://localhost:8080/logout
```

---

## Competitions

### GET /competitions
Get list of all competitions (HTML page).

**Authentication:** Required (@login_required)

**Response:**
- HTML page with competitions list
- Shows active/closed status
- Vote counts and progress bars
- Vote Now buttons for active competitions

**Example:**
```bash
curl -b "auth_token=<token>" http://localhost:8080/competitions
```

---

### GET /api/competitions
Get competitions list as JSON.

**Authentication:** Optional (public API)

**Response (200):**
```json
[
  {
    "id": 1,
    "name": "Cats vs Dogs",
    "description": "Classic competition between cats and dogs",
    "option_a": "Cats",
    "option_b": "Dogs",
    "status": "active",
    "votes_a": 42,
    "votes_b": 28,
    "created_at": "2025-10-27T10:30:00"
  },
  {
    "id": 2,
    "name": "Python vs JavaScript",
    "description": null,
    "option_a": "Python",
    "option_b": "JavaScript",
    "status": "closed",
    "votes_a": 100,
    "votes_b": 85,
    "created_at": "2025-10-27T10:45:00"
  }
]
```

**Example:**
```bash
curl http://localhost:8080/api/competitions
```

---

## Voting

### GET /vote/<competition_id>
Get vote page for specific competition.

**Authentication:** Required (@login_required)

**URL Parameters:**
- competition_id (int) - ID of competition

**Response:**
- HTML page with voting buttons
- Current vote counts
- Vote confirmation if already voted

**Example:**
```bash
curl -b "auth_token=<token>" http://localhost:8080/vote/1
```

---

### POST /vote/<competition_id>
Submit a vote for a competition.

**Authentication:** Required (@login_required)

**URL Parameters:**
- competition_id (int) - ID of competition

**Request:**
```html
Form Data:
- vote (string) - Either "a" or "b"
```

**Response:**
- Success (200): Return vote page with vote confirmed
- Error (403): Competition is closed
- Error (404): Competition not found

**Example:**
```bash
curl -X POST -b "auth_token=<token>" http://localhost:8080/vote/1 \
  -F "vote=a"
```

**Flow:**
1. User submits vote form
2. Vote saved to Redis queue
3. Worker processes vote
4. Database updated
5. Page refreshes to show updated count

---

### GET /api/admin/competitions/<competition_id>/scores
Get live vote scores for a competition.

**Authentication:** Optional (public API)

**URL Parameters:**
- competition_id (int) - ID of competition

**Response (200):**
```json
{
  "competition_id": 1,
  "a": 42,
  "b": 28
}
```

**Example:**
```bash
curl http://localhost:8080/api/admin/competitions/1/scores
```

---

## Admin Operations

### GET /admin/dashboard
Admin control panel for managing competitions.

**Authentication:** Required (@admin_required)

**Response:**
- HTML dashboard with:
  - Create competition form
  - Competitions table with live vote counts
  - Actions: Close, Open, Delete

**Example:**
```bash
curl -b "auth_token=<token>" http://localhost:8080/admin/dashboard
```

---

### POST /api/admin/competitions
Create a new competition.

**Authentication:** Required (@admin_required)

**Request:**
```json
{
  "name": "Best Framework",
  "description": "Which web framework is best?",
  "option_a": "Django",
  "option_b": "FastAPI"
}
```

**Response (201):**
```json
{
  "id": 3,
  "name": "Best Framework",
  "option_a": "Django",
  "option_b": "FastAPI",
  "status": "active",
  "created_at": "2025-10-27T11:00:00"
}
```

**Example:**
```bash
curl -X POST -b "auth_token=<token>" \
  -H "Content-Type: application/json" \
  http://localhost:8080/api/admin/competitions \
  -d '{
    "name": "Best Framework",
    "description": "Which web framework is best?",
    "option_a": "Django",
    "option_b": "FastAPI"
  }'
```

---

### POST /api/admin/competitions/<competition_id>/close
Close a competition (stop voting).

**Authentication:** Required (@admin_required)

**URL Parameters:**
- competition_id (int) - ID of competition

**Response (200):**
```json
{
  "message": "Competition closed"
}
```

**Example:**
```bash
curl -X POST -b "auth_token=<token>" \
  http://localhost:8080/api/admin/competitions/1/close
```

---

### POST /api/admin/competitions/<competition_id>/open
Reopen a closed competition.

**Authentication:** Required (@admin_required)

**URL Parameters:**
- competition_id (int) - ID of competition

**Response (200):**
```json
{
  "message": "Competition reopened"
}
```

**Example:**
```bash
curl -X POST -b "auth_token=<token>" \
  http://localhost:8080/api/admin/competitions/1/open
```

---

### DELETE /api/admin/competitions/<competition_id>
Delete a competition (and all its votes).

**Authentication:** Required (@admin_required)

**URL Parameters:**
- competition_id (int) - ID of competition

**Response (200):**
```json
{
  "message": "Competition deleted"
}
```

**Example:**
```bash
curl -X DELETE -b "auth_token=<token>" \
  http://localhost:8080/api/admin/competitions/1
```

---

## Health Checks

### GET /health
Basic health check endpoint.

**Authentication:** None

**Response (200):**
```json
{
  "status": "ok",
  "hostname": "vote-container-id"
}
```

---

### GET /ready
Readiness check (verifies Redis connectivity).

**Authentication:** None

**Response (200) - Ready:**
```json
{
  "status": "ready"
}
```

**Response (503) - Not Ready:**
```json
{
  "status": "error",
  "reason": "redis_unavailable"
}
```

---

## Authentication Details

### JWT Token Structure

Tokens are automatically created on login/register and stored in `auth_token` cookie.

**Token Contents:**
```json
{
  "user_id": 1,
  "username": "admin",
  "is_admin": true,
  "exp": 1704067200,
  "iat": 1703980800
}
```

**Expiry:** 24 hours from creation

### How to Include Token in Requests

**Option 1: Cookie** (automatic with browser)
```bash
curl -b "auth_token=<token>" http://localhost:8080/competitions
```

**Option 2: Authorization Header** (for API calls)
```bash
curl -H "Authorization: Bearer <token>" http://localhost:8080/api/competitions
```

---

## Error Responses

### 400 Bad Request
```json
{
  "error": "Invalid vote value"
}
```

### 401 Unauthorized
```json
{
  "error": "Unauthorized"
}
```

### 403 Forbidden
```json
{
  "error": "Admin access required"
}
```

### 404 Not Found
```json
{
  "error": "Competition not found"
}
```

### 500 Internal Server Error
```json
{
  "error": "Failed to create competition"
}
```

---

## Example Workflows

### Complete User Registration and Voting Flow

```bash
# 1. Register
curl -X POST http://localhost:8080/register \
  -F "username=john" \
  -F "email=john@example.com" \
  -F "password=password123" \
  -F "confirm_password=password123" \
  -c cookies.txt

# 2. Get competitions list
curl -b cookies.txt http://localhost:8080/api/competitions

# 3. Vote on competition 1, option a
curl -X POST -b cookies.txt http://localhost:8080/vote/1 \
  -F "vote=a"

# 4. Check latest scores
curl http://localhost:8080/api/admin/competitions/1/scores

# 5. Logout
curl -b cookies.txt http://localhost:8080/logout
```

### Complete Admin Workflow

```bash
# 1. Login as admin
curl -X POST http://localhost:8080/login \
  -F "username=admin" \
  -F "password=admin123" \
  -c admin_cookies.txt

# 2. Create new competition
curl -X POST -b admin_cookies.txt \
  -H "Content-Type: application/json" \
  http://localhost:8080/api/admin/competitions \
  -d '{
    "name": "Best Language",
    "option_a": "Python",
    "option_b": "Go"
  }'

# 3. Monitor voting
curl http://localhost:8080/api/admin/competitions/2/scores

# 4. Close competition after some time
curl -X POST -b admin_cookies.txt \
  http://localhost:8080/api/admin/competitions/2/close

# 5. View final results
curl http://localhost:8080/api/admin/competitions/2/scores
```

---

## Rate Limiting

Currently no rate limiting is implemented. For production:

1. Add rate limiting middleware
2. Limit votes per user per hour
3. Limit API calls to 100 requests/minute per IP

---

## CORS

Currently CORS is not configured. For production:

1. Configure allowed origins
2. Set proper CORS headers
3. Implement CSRF protection

---

**For more details, see MULTI_COMPETITION_SYSTEM.md**
