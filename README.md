# Speech to Sign Language

An AI-powered platform for converting speech to sign language in real-time, designed to bridge communication gaps and improve accessibility.

## Overview

This project provides a comprehensive solution for speech-to-sign language translation with support for:

- **Multiple Processing Modes**: On-device (privacy-focused) and cloud-based (high-accuracy)
- **Real-time Speech Recognition**: Convert speech to text using state-of-the-art AI models
- **Sign Language Translation**: Transform text into sign language with proper grammar
- **Visual Animation**: Generate 3D avatar animations or video sequences
- **Multi-language Support**: ASL, BSL, ISL, LSF, and more
- **Cross-platform**: Web app (current), iOS/Android (planned)

## Architecture

The system consists of three main components:

1. **Backend API** (Python/FastAPI)
   - Speech recognition service
   - Text-to-sign translation engine
   - Animation generation
   - Database and caching

2. **Frontend** (Coming Soon)
   - Web application (React/Vue)
   - Real-time audio capture
   - Animation playback
   - User interface

3. **Mobile Apps** (Future)
   - iOS app (Swift/SwiftUI)
   - Android app (Kotlin)
   - On-device processing

## Current Status

✅ **Backend**: Complete and ready for testing
- Speech recognition with multiple providers
- Sign language translation engine
- Animation generation framework
- RESTful API with comprehensive documentation
- Docker support for easy deployment

🚧 **Frontend**: Coming soon
- Web application for user interaction

📋 **Mobile**: Planned for post-funding

## Quick Start

### Backend Setup

```bash
# Navigate to backend directory
cd backend

# Using Docker (recommended)
docker-compose up -d

# Or local installation
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

The API will be available at:
- API: http://localhost:8000
- Interactive docs: http://localhost:8000/api/docs

For detailed backend documentation, see [backend/README.md](backend/README.md)

## Features

### Speech Recognition
- **On-device**: OpenAI Whisper (works offline, privacy-focused)
- **Cloud**: Google Cloud Speech, Azure Speech, AWS Transcribe
- Multiple language support
- Real-time and batch processing

### Sign Language Translation
- **Supported Languages**: ASL, BSL, ISL, LSF
- Grammar transformation (spoken → sign language structure)
- Context-aware translation
- Phrase library for common expressions
- Caching for performance

### Animation Generation
- **3D Avatar**: Customizable sign language avatars
- **Video Sequences**: Stitch pre-recorded sign videos
- Multiple quality levels (low/medium/high)
- Output formats: MP4, WebM, GIF
- Caption support

### Processing Modes

1. **On-Device Mode**
   - All processing on local device
   - Privacy-focused (no data sent to cloud)
   - Works offline
   - Lower resource requirements
   - Perfect for mobile deployment

2. **Cloud Mode**
   - Higher accuracy
   - More sign language features
   - Better animation quality
   - Requires internet connection

3. **Hybrid Mode** (Recommended)
   - On-device processing with cloud fallback
   - Best balance of privacy and accuracy
   - Automatic provider selection

## API Examples

### Complete Pipeline: Speech → Sign Language

```bash
curl -X POST http://localhost:8000/api/v1/animation/speech-to-sign \
  -H "Content-Type: application/json" \
  -d '{
    "audio_data": "base64_encoded_audio_data",
    "target_sign_language": "ASL",
    "output_format": "mp4",
    "include_intermediate_results": true
  }'
```

### Text to Sign Language

```bash
curl -X POST http://localhost:8000/api/v1/translation/translate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, how are you?",
    "target_sign_language": "ASL"
  }'
```

See [API Documentation](http://localhost:8000/api/docs) for more examples.

## Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL / SQLite
- **Cache**: Redis
- **Speech Recognition**: OpenAI Whisper, Google Cloud, Azure, AWS
- **Animation**: Custom 3D rendering engine
- **Deployment**: Docker, Kubernetes-ready

### Frontend (Planned)
- **Framework**: React / Vue.js
- **UI Library**: Tailwind CSS / Material-UI
- **State Management**: Redux / Pinia
- **WebRTC**: For real-time audio capture

### Mobile (Future)
- **iOS**: SwiftUI, Core ML for on-device processing
- **Android**: Kotlin, ML Kit for on-device processing

## Use Cases

- **Accessibility**: Help deaf/hard-of-hearing individuals understand spoken content
- **Education**: Learn sign language through interactive translation
- **Customer Service**: Provide sign language support in apps
- **Healthcare**: Improve communication in medical settings
- **Emergency Services**: Critical communication during emergencies
- **Video Conferencing**: Real-time sign language interpretation

## Roadmap

### Phase 1: MVP (Current)
- ✅ Backend API with core features
- ✅ Speech recognition
- ✅ Basic sign translation
- ✅ Animation generation
- ✅ Docker deployment

### Phase 2: Web Application
- [ ] React/Vue frontend
- [ ] Real-time audio capture
- [ ] Animation playback
- [ ] User preferences
- [ ] Cloud deployment

### Phase 3: Enhanced Features
- [ ] More sign languages
- [ ] ML-based translation
- [ ] Real-time WebSocket support
- [ ] User accounts and history
- [ ] Improved animations

### Phase 4: Mobile Apps
- [ ] iOS native app
- [ ] Android native app
- [ ] On-device ML models
- [ ] Offline mode
- [ ] App store deployment

### Phase 5: Advanced Features
- [ ] Reverse translation (sign → speech)
- [ ] Video input processing
- [ ] Multi-user conversations
- [ ] Educational modules
- [ ] Integration SDKs

## Configuration

The system is highly configurable through environment variables:

```bash
# Processing mode
PROCESSING_MODE=hybrid  # on-device, cloud, hybrid

# Speech recognition
SPEECH_PROVIDER=whisper
WHISPER_MODEL=base

# Sign language
DEFAULT_SIGN_LANGUAGE=ASL
ANIMATION_PROVIDER=avatar

# Performance
CACHE_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
```

See [backend/.env.example](backend/.env.example) for all options.

## Deployment

### Development
```bash
cd backend
docker-compose up
```

### Production
```bash
cd backend
# Edit docker-compose.yml for production settings
docker-compose -f docker-compose.yml --profile production up -d
```

### Cloud Platforms
- **AWS**: ECS, Lambda, or EC2
- **Google Cloud**: Cloud Run, GKE, or Compute Engine
- **Azure**: Container Instances, AKS, or VMs
- **Heroku**: Container deployment

## Performance

### On-Device (Mobile/Edge)
- Model: Whisper Tiny
- Processing: ~2-3s per utterance
- Memory: ~500MB
- Storage: ~100MB

### Cloud (Optimal)
- Model: Whisper Large
- Processing: ~1s per utterance
- Concurrent requests: 100+
- Scalable infrastructure

## Contributing

We welcome contributions! Areas where you can help:

- **Sign Language Dictionaries**: Add words/phrases for different sign languages
- **Animations**: Create or improve 3D avatar animations
- **Translations**: Improve translation algorithms
- **Testing**: Test on different platforms and languages
- **Documentation**: Improve docs and tutorials
- **Frontend**: Build the web/mobile interfaces

Please see CONTRIBUTING.md for guidelines.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Acknowledgments

- OpenAI Whisper for speech recognition
- Sign language communities and dictionaries
- FastAPI framework
- Open-source contributors

## Contact

For questions, feedback, or collaboration:
- Issues: GitHub Issues
- Email: your-email@example.com
- Website: https://yourproject.com

## Support the Project

This project is open-source and free to use. If you find it valuable:
- ⭐ Star the repository
- 🐛 Report bugs
- 💡 Suggest features
- 🤝 Contribute code
- 📢 Spread the word

---

**Built with ❤️ to improve accessibility and communication**
