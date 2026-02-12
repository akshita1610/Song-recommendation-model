# Modern Song Recommendation System - Web Interface

A modern, async-ready song recommendation system built with FastAPI, Spotify API, and cutting-edge Python technologies.

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Spotify Developer Account
- Git

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd song-recommendation-model

# Set up environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .[api]

# Setup environment
cp .env.example .env
# Edit .env with your Spotify credentials
```

### Running the Application

```bash
# Development mode
uvicorn src.api:app --reload --host 0.0.0.0 --port 8000

# Or using the Makefile
make run-api
```

Visit http://localhost:8000 to access the web interface.

## 🌐 Web Interface Features

### **Modern Web UI**
- **Responsive Design**: Works on all devices
- **Bootstrap 5**: Modern, clean interface
- **Interactive Elements**: Smooth animations and transitions
- **Real-time Search**: Instant track discovery

### **RESTful API**
- **FastAPI**: High-performance async framework
- **Auto-documentation**: Interactive API docs at `/docs`
- **OpenAPI**: Standardized API specification
- **CORS Support**: Cross-origin requests enabled

### **Authentication & Security**
- **JWT Tokens**: Secure authentication
- **Password Hashing**: bcrypt encryption
- **Rate Limiting**: API protection
- **Input Validation**: Pydantic models

## 📡 API Endpoints

### **Core Endpoints**

#### `GET /`
- **Description**: Home page with search interface
- **Response**: HTML page

#### `GET /api/v1/health`
- **Description**: Health check endpoint
- **Response**: 
```json
{
  "status": "healthy",
  "service": "song-recommendation-api",
  "version": "2.0.0"
}
```

#### `POST /api/v1/recommendations`
- **Description**: Get song recommendations
- **Request Body**:
```json
{
  "track_ids": ["4iV5W9uYEdYUVa79Axb7Rh"],
  "limit": 20,
  "target_energy": 0.8,
  "target_danceability": 0.7,
  "target_valence": 0.9
}
```
- **Response**:
```json
{
  "recommendations": [...],
  "count": 20,
  "processing_time_ms": 245.67,
  "algorithm_used": "spotify_recommendations"
}
```

#### `GET /api/v1/search`
- **Description**: Search for tracks
- **Query Parameters**:
  - `query` (required): Search string
  - `limit` (optional): Number of results (1-50)
  - `market` (optional): Market code (default: US)
- **Response**: Array of track objects

#### `GET /api/v1/playlist/{playlist_id}`
- **Description**: Get tracks from a playlist
- **Response**: Playlist object with tracks array

#### `GET /api/v1/track/{track_id}`
- **Description**: Get detailed track information
- **Response**: Track object with full metadata

#### `GET /api/v1/track/{track_id}/features`
- **Description**: Get audio features for a track
- **Response**: Audio features object

### **Authentication Endpoints**

#### `POST /token`
- **Description**: Authenticate user and get JWT token
- **Request Body**:
```json
{
  "username": "your_username",
  "password": "your_password"
}
```
- **Response**:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

## 🔧 Configuration

### **Environment Variables**

Create a `.env` file with:

```bash
# Spotify API Configuration
SPOTIPY_CLIENT_ID=your_spotify_client_id
SPOTIPY_CLIENT_SECRET=your_spotify_client_secret
SPOTIPY_REDIRECT_URI=http://localhost:8888/callback

# Security
SECRET_KEY=your_super_secret_key_here

# Application
DEBUG=False
LOG_LEVEL=INFO
```

### **Advanced Configuration**

The system supports extensive configuration through environment variables and Pydantic models:

- **Cache Configuration**: TTL, storage paths
- **Rate Limiting**: Requests per window
- **Logging**: Levels, file paths
- **API Limits**: Max requests, timeouts

## 🧪 Development

### **Code Quality Tools**

```bash
# Format code
make format

# Run linting
make lint

# Type checking
make type-check

# Run tests
make test

# All quality checks
make ci
```

### **Testing**

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_spotify_client.py -v
```

### **API Testing**

The API includes comprehensive test coverage:

- **Unit Tests**: Individual component testing
- **Integration Tests**: API endpoint testing
- **Async Tests**: Proper async/await testing
- **Mock Testing**: External API mocking

## 📊 Performance Features

### **Caching Strategy**
- **Multi-Level Caching**: Memory + File + Redis (production)
- **Intelligent TTL**: Configurable expiration
- **Cache Invalidation**: Smart cache management

### **Async Architecture**
- **Non-blocking I/O**: All API calls are async
- **Concurrent Processing**: Multiple requests handled simultaneously
- **Resource Efficiency**: Optimized memory usage

### **Rate Limiting**
- **User-based Limits**: Per-user request tracking
- **Sliding Window**: Time-based rate limiting
- **Graceful Degradation**: 429 responses with retry info

## 🔒 Security Features

### **Authentication**
- **JWT Tokens**: Secure stateless authentication
- **Password Security**: bcrypt hashing with salt
- **Token Expiration**: Configurable token lifetime
- **Scope-based Access**: Role-based permissions

### **Input Validation**
- **Pydantic Models**: Type-safe input validation
- **SQL Injection Protection**: Parameterized queries
- **XSS Prevention**: Output sanitization
- **Rate Limiting**: DDoS protection

### **HTTPS Support**
- **SSL/TLS**: Encrypted communication
- **CORS Configuration**: Secure cross-origin requests
- **Security Headers**: HSTS, CSP, etc.

## 📈 Monitoring & Logging

### **Structured Logging**
```python
# Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
logger.info("User authenticated successfully", extra={
    "user_id": user.id,
    "ip_address": request.client.host
})
```

### **Performance Monitoring**
- **Response Times**: Track API performance
- **Cache Hit Rates**: Monitor caching efficiency
- **Error Rates**: Track system health
- **User Analytics**: Usage patterns

## 🚀 Deployment

### **Production Setup**

```bash
# Install production dependencies
pip install -e .[prod]

# Set production environment
export DEBUG=False
export LOG_LEVEL=WARNING

# Run with Gunicorn
gunicorn src.api:app -w 4 -k uvicorn.workers.UvicornWorker
```

### **Docker Deployment**

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements/prod.txt .
RUN pip install -r prod.txt

COPY . .
EXPOSE 8000

CMD ["gunicorn", "src.api:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker"]
```

### **Environment Configuration**

- **Development**: SQLite, debug logging, hot reload
- **Staging**: PostgreSQL, structured logging
- **Production**: PostgreSQL + Redis, monitoring

## 🎯 API Usage Examples

### **JavaScript/TypeScript**

```typescript
interface Track {
  id: string;
  name: string;
  artist: string;
  album: string;
  uri: string;
  duration_ms: number;
  popularity: number;
}

// Get recommendations
async function getRecommendations(trackIds: string[]): Promise<Track[]> {
  const response = await fetch('/api/v1/recommendations', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      track_ids: trackIds,
      limit: 20
    })
  });
  
  const data = await response.json();
  return data.recommendations;
}
```

### **Python**

```python
import httpx

async def get_recommendations(track_ids: list[str]) -> list[dict]:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/recommendations",
            json={"track_ids": track_ids, "limit": 20}
        )
        return response.json()["recommendations"]
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run quality checks: `make ci`
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

---

## 🎵 Built With Modern Tech Stack

- **FastAPI**: Modern, fast web framework
- **Pydantic**: Data validation and serialization
- **Spotify API**: Extensive music library
- **Async Python**: High-performance concurrency
- **JWT**: Secure authentication
- **Bootstrap 5**: Modern UI components
- **Docker**: Containerization support

Visit the interactive API documentation at http://localhost:8000/docs
