# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-02-22

### Added

#### Project Structure
- Initial project structure with proper Python package layout
- Configuration via `pyproject.toml` with hatchling build system
- CLI entry point `auto-video` with subcommands

#### Configuration System
- Pydantic-based configuration schemas (`AppConfig`, `LLMProviderConfig`, `TTSConfig`, etc.)
- YAML configuration file support with environment variable substitution
- Secure file permissions for configuration files
- Configuration loader and saver with validation

#### Workspace Management
- Automatic workspace creation per video project
- Unique video ID generation (timestamp + UUID)
- Artifact tracking (script, audio, video, subtitles, thumbnail, logs)
- Cleanup functionality with optional artifact preservation

#### Setup Wizard
- Interactive TUI setup wizard for first-time configuration
- LLM configuration wizard (API/Local/Hybrid modes)
- Storage configuration wizard
- Visuals configuration wizard (Stock API/Local/Generated/Hybrid)
- TTS and Image generation configuration wizard
- YouTube OAuth configuration wizard
- Prompts customization wizard

#### LLM Module
- Abstract `LLMProvider` base class
- OpenAI provider with retry logic and rate limiting
- Anthropic provider with streaming support
- Groq provider for fast inference
- Google provider for Gemini API
- Ollama provider for local models
- Llama.cpp provider (optional)
- Script generation, keyword extraction, and image prompt generation

#### TTS Module
- Abstract `TTSProvider` base class
- Kokoro TTS provider for local synthesis
- ElevenLabs provider with quota management
- OpenAI TTS provider with caching
- Text segmentation and audio concatenation
- Voice selection support

#### Stock Footage Module
- Abstract `StockProvider` base class
- Pexels provider with search and download
- Pixabay provider with search and download
- Stock manager for multiple providers
- Quality selection (high/medium/low)
- Automatic clip selection based on duration

#### Video Module
- Local assets manager for video/photo files
- Video composer using FFmpeg
- Clip concatenation with target duration
- Audio/video merging
- Format conversion (short 9:16 / long 16:9)

#### Subtitles Module
- Whisper-based transcription
- SRT subtitle generation
- Subtitle burning into video
- Configurable subtitle styles

#### Thumbnail Module
- Image generation from context
- Z-Image provider for local generation
- OpenAI DALL-E provider for API generation
- LLM-powered image prompt generation

#### YouTube Upload Module
- OAuth2 authentication flow
- Video upload with progress tracking
- Thumbnail upload
- Quota management
- Privacy settings (public/unlisted/private)

#### Pipeline
- Orchestrated video creation pipeline
- Step-by-step execution (Script → Audio → Visuals → Montage → Subtitles → Thumbnail → Upload)
- State persistence for resume capability
- Error recovery and retry logic
- Progress display with Rich TUI

#### CLI Commands
- `auto-video setup` - Interactive configuration wizard
- `auto-video create` - Create a new video
- `auto-video resume` - Resume interrupted video creation
- `auto-video config` - View/edit configuration
- `auto-video models` - Manage downloaded models
- `auto-video --version` - Show version

#### Security
- API key masking in logs
- Secure file permissions (0600 for credentials)
- Filename sanitization
- Path traversal protection
- Video ID validation

#### Logging
- Structured logging system
- Video-scoped loggers
- Step start/end logging
- API call tracking

#### Documentation
- README with installation and usage guide
- ARCHITECTURE documentation
- PIPELINE documentation
- MODELS documentation
- API documentation
- SETUP guide
- Advanced configuration guide

### Dependencies

#### Core
- Python 3.10+
- rich >= 13.0.0
- pydantic >= 2.0.0
- pyyaml >= 6.0
- tenacity >= 8.0.0
- httpx >= 0.25.0
- openai >= 1.0.0
- tomli >= 2.0.0 (Python < 3.11)

#### Optional
- ollama (for local LLM)
- torch, scipy (for local TTS)
- openai-whisper (for local STT)
- diffusers, transformers, accelerate (for local image generation)
- google-auth, google-auth-oauthlib, google-api-python-client (for YouTube)

#### Development
- pytest >= 7.0.0
- pytest-cov >= 4.0.0
- ruff >= 0.1.0
- mypy >= 1.0.0

### Testing
- Comprehensive test suite with 150+ tests
- Unit tests for all modules
- Integration tests for pipeline
- Mock providers for testing

[1.0.0]: https://github.com/user/auto-video/releases/tag/v1.0.0
