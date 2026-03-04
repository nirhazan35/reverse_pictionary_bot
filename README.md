# Reverse Pictionary Bot 🎨🤖

A multiplayer AI-powered game built as a Telegram Bot where players compete to write the best text description of an AI-generated target image. The bot generates images from player prompts using SDXL Turbo and scores similarity using Jina CLIP v2.

## 🎮 How It Works

1. A game starts in a Telegram group with a random AI-generated target image
2. Players have a limited time to write text prompts describing the image
3. Each prompt is sent to an ML API that generates a new image
4. The generated images are compared to the target using deep-learning similarity scoring
5. The player whose description produces the most similar image wins!

## 🏗️ Architecture

The project consists of two decoupled services:

### Telegram Bot (This Repository)
- **Language:** Python 3.14
- **Framework:** pyTeleBot (Telegram Bot API wrapper)
- **Package Manager:** `uv`
- Handles game flow, player interactions, and coordination

### ML Inference API (Separate Service)
- **Runtime:** Kaggle Notebook with GPU acceleration
- **Framework:** FastAPI + ngrok tunneling
- **Models:**
  - **SDXL Turbo** for text-to-image generation
  - **Jina CLIP v2** for image similarity scoring

## 📁 Project Structure

```
├── bot.py                  # Bot entry point and initialization
├── config.py               # Configuration and environment variables
├── handlers.py             # Telegram command and message handlers
├── game_logic.py          # Core game flow and phase transitions
├── game_state.py          # Thread-safe game state management
├── challenge_api.py       # HTTP client for fetching target images
├── evaluation_api.py      # HTTP client for prompt evaluation
├── pyproject.toml         # Python project dependencies
└── notebooks/
    └── model_pipeline.ipynb  # ML model development
```

## 🚀 Setup

### Prerequisites

- Python 3.13 or higher (3.14+ recommended)
- `uv` package manager ([installation guide](https://docs.astral.sh/uv/))
- A Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- Access to the ML inference API

### Installation

1. Clone the repository:
```bash
git clone https://github.com/nirhazan35/reverse_pictionary_bot.git
cd reverse_pictionary_bot
```

2. Install dependencies:
```bash
uv sync
```

3. Create a `.env` file in the project root:
```env
BOT_TOKEN=your_telegram_bot_token_here
API_BASE_URL=https://your-ml-api-url.ngrok.io
GROUP_LINK=https://t.me/your_game_group
HEALTH_CHECK_ENABLED=true
```

### Configuration

Edit [config.py](config.py) to customize game parameters:
- `LOBBY_DURATION`: Time to wait for players to join (default: 30 seconds)
- `LOBBY_TICK`: Lobby countdown update interval (default: 10 seconds)
- `GUESS_DURATION`: Time players have to submit guesses (default: 30 seconds)
- `GUESS_TICK`: Guess countdown update interval (default: 10 seconds)
- `MIN_PLAYERS`: Minimum players required to start a game (default: 1)
- `API_TIMEOUT_CHALLENGE`: Timeout for fetching target images (default: 30 seconds)
- `API_TIMEOUT_EVALUATE`: Timeout for evaluation API (default: 50 seconds)
- `HEALTH_CHECK_ENABLED`: Whether to perform health check on startup (default: True)

## 🎯 Usage

### Running the Bot

```bash
uv run bot.py
```

The bot will:
1. Perform a health check against the ML API (if enabled)
2. Register all command handlers
3. Start polling for Telegram messages

**Note:** Always use `uv run` to ensure the correct virtual environment is used.

### Available Commands

- `/start` - Get started and receive instructions
- `/start_game` - Start a new game in a group chat
- `/guess` - Submit your description (in private chat with bot)

### Playing a Game

1. Add the bot to a Telegram group
2. Use `/start_game` to begin
3. Wait for players to join during the lobby phase
4. Each player clicks "Join Game" and submits their guess privately
5. After the timer expires, the bot evaluates all guesses and announces the winner!

## 🛠️ Development

### Running with Development Tools

The project includes development dependencies in `pyproject.toml`:
- `ipython` for enhanced REPL
- `ruff` for linting and formatting

### Code Quality

Format code with ruff:
```bash
uv run ruff format .
```

Lint code:
```bash
uv run ruff check .
```

### Interactive Development

Launch IPython for interactive testing:
```bash
uv run ipython
```

## 📝 Project Background

This project was developed during the **DevBoost Hackathon** (February 2026) and demonstrates full-stack AI engineering, combining:
- Real-time multiplayer game logic
- Telegram bot development with pyTeleBot
- Thread-safe state management for concurrent players
- GPU-accelerated ML inference with FastAPI
- Deep learning models for image generation and similarity
- Asynchronous API communication with proper timeout handling

## 🔧 Troubleshooting

### Common Issues

**ModuleNotFoundError: No module named 'telebot'**
- Solution: Run `uv sync` to install dependencies, then use `uv run bot.py`

**Health check failed**
- Ensure the ML API is running and accessible
- Check that `API_BASE_URL` in `.env` is correct
- Set `HEALTH_CHECK_ENABLED=false` in `.env` to skip health checks during development

**Bot not responding**
- Verify `BOT_TOKEN` in `.env` is correct
- Check that the bot has proper permissions in the Telegram group
- Ensure you're using `/start_game` in a group chat, not private chat

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 👤 Author

Nir Hazan

---

**Built with ❤️ using Python, Telegram Bot API, SDXL Turbo, and Jina CLIP v2**
