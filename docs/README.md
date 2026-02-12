# Song Recommendation System Documentation

## Overview
A modern song recommendation system built with Python, Streamlit, and machine learning.

## Features
- Personalized song recommendations
- Multiple recommendation algorithms
- User preference tracking
- Audio feature analysis
- Modern async architecture

## Quick Start

### Installation
```bash
# Clone the repository
git clone <repository-url>
cd song-recommendation-model

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements/dev.txt

# Setup environment
cp .env.example .env
# Edit .env with your Spotify credentials
```

### Running the Application
```bash
streamlit run main.py
```

## Architecture

### Project Structure
```
song-recommendation-model/
├── src/                    # Source code
│   ├── core/              # Core functionality
│   ├── web/               # Web interface components
│   ├── data_models.py     # Data structures
│   ├── exceptions.py      # Custom exceptions
│   ├── logging_config.py  # Logging setup
│   ├── recommendation_engine.py # ML engine
│   ├── spotify_client.py  # Spotify API client
│   ├── user_manager.py    # User management
│   └── validators.py      # Input validation
├── tests/                 # Test files
├── docs/                  # Documentation
├── config/                # Configuration files
├── data/                  # Data files
├── model/                 # ML models
├── requirements/          # Dependencies
├── main.py               # Application entry point
└── pyproject.toml        # Project configuration
```

### Core Components

#### SpotifyClient (`src/spotify_client.py`)
- Async Spotify API interactions
- Multi-level caching
- Audio feature extraction
- Similarity calculations

#### RecommendationEngine (`src/recommendation_engine.py`)
- Multiple recommendation algorithms
- Vectorized operations
- ML model integration
- Performance optimization

#### UserManager (`src/user_manager.py`)
- User authentication
- Preference tracking
- SQLite database operations
- Session management

## Development

### Code Quality
```bash
# Format code
black src/ main.py
isort src/ main.py

# Type checking
mypy src/

# Linting
flake8 src/ main.py

# Run tests
pytest tests/
```

### Pre-commit Hooks
```bash
pre-commit install  # Install hooks
pre-commit run --all-files  # Run all checks
```

## Configuration

### Environment Variables
See `.env.example` for all available configuration options.

### Spotify API Setup
1. Create a Spotify Developer account
2. Create a new application
3. Get Client ID and Client Secret
4. Add to `.env` file

## Deployment

### Production Setup
```bash
# Install production dependencies
pip install -r requirements/prod.txt

# Run with Gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
```

## API Reference

### Data Models
- `Track`: Represents a music track
- `User`: User account and preferences
- `RecommendationResult`: Recommendation output
- `AudioFeatures`: Track audio characteristics

### Exceptions
- `SongRecommendationError`: Base exception
- `SpotifyAPIError`: Spotify API failures
- `DatabaseError`: Database operation failures
- `AuthenticationError`: User authentication issues

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with proper tests
4. Run code quality checks
5. Submit a pull request

## License

MIT License - see LICENSE file for details.
