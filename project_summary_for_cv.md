# Reverse Pictionary Bot — Project Summary for CV

## Project Overview

**Reverse Pictionary Bot** is a multiplayer AI-powered game built as a **Telegram Bot** during a hackathon (DevBoost Hackathon, February 2026). Players receive an AI-generated target image and must write text prompts that describe it as accurately as possible. The system then generates a new image from each player's prompt using a text-to-image AI model and scores how closely it matches the original using deep-learning-based image similarity. The best description wins.

This project demonstrates **full-stack AI engineering**: designing and deploying a real-time multiplayer game that combines a **Telegram chatbot** (Python, pyTeleBot) with a **GPU-accelerated machine-learning inference API** (Kaggle Notebook, FastAPI, SDXL Turbo, Jina CLIP v2).

---

## Architecture

The system is composed of two independent, decoupled services:

### 1. Telegram Bot (Client Application)

- **Language:** Python 3.13
- **Framework:** pyTeleBot (Telegram Bot API wrapper)
- **Package Manager:** `uv` (modern Python package manager)
- **Environment:** Runs locally or on any server; communicates with the Telegram API and the ML backend API.
- **Source Files:**
  - `bot.py` — Application entry point. Initializes the bot, registers handlers, performs a startup health check against the ML API, and starts long-polling.
  - `config.py` — Centralized configuration module. Loads secrets (`BOT_TOKEN`, `GROUP_LINK`, `API_BASE_URL`) from a `.env` file, defines API route URLs, tunable game parameters (lobby duration, guess duration, tick intervals, minimum players), and API timeout settings.
  - `handlers.py` — All Telegram command and message handlers (`/start`, `/start_game`, `/guess`, join-game callback, DM message handler). Implements deep-link routing for private guess submission.
  - `game_logic.py` — Core game flow: lobby countdown, guess countdown, phase transitions (IDLE → LOBBY → GUESSING → EVALUATING), asynchronous per-player evaluation with eager API calls, result aggregation and announcement.
  - `game_state.py` — Thread-safe shared game state management using a Python `threading.Lock` and a global dictionary tracking status, players, guesses, evaluation results, Telegram message IDs, and countdown timers.
  - `challenge_api.py` — HTTP client for the `/get_image` API endpoint. Fetches a random target image (base64-encoded PNG) and its ID from the ML backend.
  - `evaluation_api.py` — HTTP client for the `/play_round` API endpoint. Sends a player's text prompt + target image ID, receives a similarity score (0–100%) and the generated image (base64-encoded PNG).

### 2. ML Inference API (Backend — Kaggle Notebook)

- **Runtime:** Kaggle Notebook with **GPU acceleration** (CUDA)
- **Language:** Python 3.12
- **File:** `Hackathon Devboost.ipynb`
- **Framework:** FastAPI + Uvicorn (ASGI server), exposed to the internet via **ngrok** tunneling with a static domain
- **Key Libraries:** PyTorch, HuggingFace Transformers, HuggingFace Diffusers, scikit-learn, Pillow, nest-asyncio, pyngrok

#### Models Used

| Model | Purpose | Details |
|---|---|---|
| **Jina CLIP v2** (`jinaai/jina-clip-v2`) | Image–text similarity scoring | A multimodal embedding model that encodes both images and text into a shared vector space. Used to compute cosine similarity between the target image embedding and the player's generated image embedding. Model size: ~1.73 GB. |
| **SDXL Turbo** (`stabilityai/sdxl-turbo`) | Text-to-image generation | A fast, high-quality diffusion model for real-time image generation. Runs with only **3 inference steps** and `guidance_scale=0.0` for ultra-fast generation. Loaded in **FP16** precision with attention slicing for GPU memory efficiency. Model size: ~5.14 GB (UNet) + ~1.39 GB (text encoder 2) + ~246 MB (text encoder 1) + ~167 MB (VAE). |

#### API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Returns server health status and whether the GPU lock is currently held. |
| `/get_image` | GET | Randomly selects a target image from a pre-loaded dataset, returns it as base64-encoded PNG along with its ID. |
| `/play_round` | POST | Accepts `user_prompt` and `target_image_id`. Generates an image from the prompt using SDXL Turbo, computes similarity score against the pre-computed target image embedding using Jina CLIP v2, returns the score and generated image. |

#### Key Implementation Details

- **Pre-computed embeddings:** Target image embeddings are pre-computed and stored in a JSON file (`embeddings.json`) alongside the image dataset. This avoids redundant GPU inference during gameplay.
- **GPU concurrency control:** An `asyncio.Lock` (`gpu_lock`) serializes all GPU-intensive operations (image generation + embedding) to prevent out-of-memory errors.
- **Similarity scoring formula:** Raw cosine similarity is transformed to a 0–100% scale using: `display_score = max(0, (cosine_sim - 0.4) / 0.6) * 100`, which maps the practical similarity range (~0.4–1.0) to a human-readable percentage.
- **Memory management:** After each evaluation, `torch.cuda.empty_cache()` and `gc.collect()` are called to free GPU memory.
- **Ngrok tunneling:** The notebook uses `pyngrok` to create a secure HTTPS tunnel from the Kaggle environment to a static ngrok domain, making the API accessible to the Telegram bot over the public internet.
- **Kaggle Secrets:** The ngrok auth token and static domain are securely stored using Kaggle's `UserSecretsClient`.

---

## Game Flow

1. **Start:** A user types `/start_game` in the Telegram group → a lobby is created with a **30-second** join countdown.
2. **Join:** Players click the "Join Game" inline button. The lobby message live-updates with the player count and remaining time.
3. **Challenge:** When the lobby timer ends, the bot fetches a random target image from the ML API and posts it to the group.
4. **Guess:** Players click "Submit Guess Privately" (a deep-link) to open a private DM with the bot, where they see the target image with a live countdown timer and type their text prompt.
5. **Eager Evaluation:** Each guess is immediately sent to the ML API in a background thread for evaluation (image generation + similarity scoring), rather than waiting until all guesses are collected. This prevents API overload and reduces end-of-round latency.
6. **Results:** When the guess timer expires (or all players have submitted and their evaluations are complete), the bot posts a ranked leaderboard with scores and each player's generated image to the group.

---

## Technical Skills Demonstrated

- **Machine Learning & Deep Learning:** Deploying and orchestrating multiple large pre-trained models (diffusion model for image generation, CLIP model for multimodal embeddings) on GPU for real-time inference.
- **API Design & Development:** Building a RESTful API with FastAPI, including health checks, async request handling, and GPU resource management.
- **Python Backend Development:** Multi-threaded game state management with thread-safe locking, asynchronous evaluation pipeline, modular codebase architecture.
- **Chatbot Development:** Building an interactive multiplayer Telegram bot with inline keyboards, deep-links, private DM interactions, live-updating messages, and callback query handlers.
- **Cloud & Infrastructure:** Running GPU-accelerated ML workloads on Kaggle, exposing services via ngrok tunneling, managing secrets securely.
- **Full-Stack Integration:** End-to-end system connecting a user-facing chat interface to a GPU-powered ML backend over HTTP.
- **Software Engineering Best Practices:** Separation of concerns (handlers, game logic, game state, API clients, configuration), centralized config with `.env` secrets, structured logging, error handling, health checks at startup.

---

## Technologies & Tools

| Category | Technologies |
|---|---|
| **Languages** | Python |
| **Bot Framework** | pyTeleBot (Telegram Bot API) |
| **ML Frameworks** | PyTorch, HuggingFace Transformers, HuggingFace Diffusers |
| **ML Models** | SDXL Turbo (text-to-image), Jina CLIP v2 (image-text similarity) |
| **API Framework** | FastAPI, Uvicorn |
| **Infrastructure** | Kaggle Notebooks (GPU), ngrok (tunneling) |
| **Other Libraries** | scikit-learn (cosine similarity), Pillow (image processing), nest-asyncio, pyngrok |
| **Package Management** | uv, pip |
| **Secrets Management** | python-dotenv, Kaggle UserSecretsClient |
