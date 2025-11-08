# Speech to Sign Language - Backend API

A comprehensive backend system for converting speech to sign language, supporting both on-device and cloud-based processing.

## Features

- **Speech Recognition**: Convert audio to text using multiple providers
  - On-device: OpenAI Whisper
  - Cloud: Google Cloud Speech, Azure Speech, AWS Transcribe

- **Text to Sign Translation**: Convert text to sign language sequences
  - Multiple sign languages (ASL, BSL, ISL, LSF)
  - Grammar transformation for sign language structure
  - Caching for improved performance

- **Sign Language Animation**: Generate visual representations
  - 3D avatar animations
  - Video sequence stitching
  - Multiple output formats (MP4, WebM, GIF)

- **Dual Processing Modes**:
  - On-device: Privacy-focused, works offline
  - Cloud: Higher accuracy, more features
  - Hybrid: Best of both worlds

## Architecture

```
backend/
├── main.py                 # FastAPI application entry point
├── app/
│   ├── config.py          # Configuration management
│   ├── database.py        # Database setup
│   ├── schemas.py         # Pydantic models
│   ├── models/            # SQLAlchemy models
│   │   └── sign_dictionary.py
│   ├── services/          # Business logic
│   │   ├── speech_recognition.py
│   │   ├── translation.py
│   │   └── animation.py
│   ├── routes/            # API endpoints
│   │   ├── health.py
│   │   ├── speech.py
│   │   ├── translation.py
│   │   └── animation.py
│   └── middleware/        # Custom middleware
│       ├── auth.py
│       └── rate_limit.py
├── requirements.txt       # Full dependencies
├── requirements-minimal.txt  # Minimal dependencies for on-device
├── Dockerfile
└── docker-compose.yml
```

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone the repository
cd backend

# Copy environment file
cp .env.example .env

# Edit .env with your settings
nano .env

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# The API will be available at http://localhost:8000
# API docs at http://localhost:8000/api/docs
```

### Option 2: Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your settings

# Set up database
# Make sure PostgreSQL is running, then:
python -c "from app.database import Base, engine; Base.metadata.create_all(bind=engine)"

# Run the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Option 3: On-Device Minimal Setup

For resource-constrained environments (mobile, edge devices):

```bash
# Use minimal requirements
pip install -r requirements-minimal.txt

# Use SQLite instead of PostgreSQL
# In .env set: DATABASE_URL=sqlite:///./sign_language.db

# Run with single worker
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
```

## API Documentation

Once the server is running, visit:

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

### Key Endpoints

#### Speech Recognition

```bash
# Recognize speech from base64 audio
POST /api/v1/speech/recognize
{
  "audio_data": "base64_encoded_audio",
  "language": "en-US",
  "provider": "whisper"
}

# Upload audio file
POST /api/v1/speech/recognize/upload
multipart/form-data with audio file
```

#### Translation

```bash
# Translate text to sign language
POST /api/v1/translation/translate
{
  "text": "Hello, how are you?",
  "target_sign_language": "ASL",
  "include_animation": true
}
```

#### Animation

```bash
# Generate animation from sign sequence
POST /api/v1/animation/generate
{
  "sign_sequence": ["HELLO", "HOW", "YOU"],
  "sign_language": "ASL",
  "output_format": "mp4",
  "quality": "medium"
}

# Complete pipeline: Speech -> Sign -> Animation
POST /api/v1/animation/speech-to-sign
{
  "audio_data": "base64_encoded_audio",
  "target_sign_language": "ASL",
  "output_format": "mp4",
  "include_intermediate_results": true
}
```

## Configuration

All configuration is managed through environment variables. See `.env.example` for all options.

### Key Settings

```bash
# Processing mode
PROCESSING_MODE=hybrid  # on-device, cloud, hybrid

# Speech recognition
SPEECH_PROVIDER=whisper
WHISPER_MODEL=base  # tiny, base, small, medium, large

# Sign language
DEFAULT_SIGN_LANGUAGE=ASL
ANIMATION_PROVIDER=avatar  # avatar, video, hybrid

# Performance
CACHE_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
```

## Database Setup

The system uses PostgreSQL by default. To set up the database:

```bash
# Using Docker
docker-compose up -d postgres

# Or install PostgreSQL locally
# Ubuntu/Debian:
sudo apt-get install postgresql postgresql-contrib

# macOS:
brew install postgresql

# Create database
createdb sign_language_db

# Run migrations (if using Alembic)
alembic upgrade head
```

## Cloud Provider Setup

### Google Cloud Speech

1. Create a Google Cloud project
2. Enable Speech-to-Text API
3. Create a service account and download JSON key
4. Set environment variables:
   ```bash
   GOOGLE_CLOUD_PROJECT=your-project-id
   GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
   ```

### Azure Speech

1. Create Azure Cognitive Services resource
2. Get your subscription key and region
3. Set environment variables:
   ```bash
   AZURE_SPEECH_KEY=your-key
   AZURE_SPEECH_REGION=eastus
   ```

### AWS Transcribe

1. Create AWS account and IAM user
2. Get access credentials
3. Set environment variables:
   ```bash
   AWS_ACCESS_KEY_ID=your-key-id
   AWS_SECRET_ACCESS_KEY=your-secret-key
   AWS_REGION=us-east-1
   ```

## Performance Optimization

### On-Device Deployment

- Use `requirements-minimal.txt`
- Use Whisper `tiny` or `base` model
- Enable caching: `CACHE_ENABLED=true`
- Use SQLite: `DATABASE_URL=sqlite:///./sign_language.db`
- Single worker: `--workers 1`

### Cloud Deployment

- Use larger Whisper models (`medium`, `large`)
- Enable Redis caching
- Use PostgreSQL
- Multiple workers: `--workers 4`
- Consider GPU: `WHISPER_DEVICE=cuda`

## Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov httpx

# Run tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_speech_recognition.py
```

## Production Deployment

### Using Docker Swarm

```bash
docker stack deploy -c docker-compose.yml sign-language
```

### Using Kubernetes

See `k8s/` directory for Kubernetes manifests (coming soon).

### Environment Variables for Production

```bash
ENVIRONMENT=production
API_KEY_ENABLED=true
RATE_LIMIT_ENABLED=true
LOG_LEVEL=WARNING
```

## Monitoring

Health check endpoints:

- `/api/v1/health` - Detailed health status
- `/api/v1/health/ready` - Kubernetes readiness probe
- `/api/v1/health/live` - Kubernetes liveness probe

## Roadmap

- [ ] Add more sign languages (JSL, Auslan, etc.)
- [ ] ML-based translation models
- [ ] Real-time WebSocket support
- [ ] Mobile SDK (iOS/Android)
- [ ] WebAssembly for in-browser processing
- [ ] Sign language recognition (reverse translation)
- [ ] User authentication and profiles
- [ ] Learning mode with feedback

## Contributing

Contributions welcome! Please see CONTRIBUTING.md for guidelines.

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:
- GitHub Issues: https://github.com/yourusername/speech-to-sign-language/issues
- Documentation: https://docs.yourproject.com

## Acknowledgments

- OpenAI Whisper for speech recognition
- Sign language dictionaries and resources
- FastAPI framework
- Open-source sign language community
