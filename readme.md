# Maakima Bot: Voice Assistant with LiveKit Integration

## Overview

This project implements a voice assistant bot that integrates with LiveKit to provide interactive, real-time communication. The bot not only joins LiveKit rooms using a generated token but also handles conversational interactions and email operations. It leverages several technologies:
- **Deepgram** for speech-to-text (STT)
- **Silero** for voice activity detection (VAD)
- **OpenAI** for conversational AI (LLM) and text-to-speech (TTS)
- Email protocols for sending and reading emails

## Features

- **LiveKit Integration**
  - Generates a bot token using LiveKit API credentials.
  - Connects to a specified LiveKit room over WebSocket.
  
- **Voice Assistant**
  - Listens for voice and chat messages.
  - Responds using a conversational language model.
  - Provides interactive responses and can execute function calls.
  
- **Email Operations**
  - **Send Email:** Sends an email after validating the recipient’s email address.
  - **Read Email Subjects:** Retrieves subjects of the latest emails from the inbox.
  
- **Web API**
  - Exposes an HTTP endpoint (`POST /join-room`) to trigger the bot to join a LiveKit room.

## Prerequisites

- Python 3.8 or later
- A virtual environment (recommended)
- API keys and credentials for:
  - Deepgram (for STT)
  - LiveKit (API key and secret)
  - SMTP/IMAP servers for email operations

## Installation

1. **Clone the Repository:**
   ```bash
   git clone <repository-url>
   cd <repository-folder>
   ```

2. **Set Up a Virtual Environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables:**
   Create a `.env` file in the project root with the following contents:
   ```dotenv
   DEEPGRAM_API_KEY=your-deepgram-api-key
   LIVEKIT_URL=wss://your-livekit-url
   LIVEKIT_API_KEY=your-livekit-api-key
   LIVEKIT_API_SECRET=your-livekit-api-secret
   SENDER_EMAIL=your-email@example.com
   SMTP_SERVER=smtp.example.com
   SMTP_PORT=587
   SMTP_PASSWORD=your-smtp-password
   ```
   Adjust the values to match your configuration.

## Usage

1. **Start the Bot:**
   Run the main script to launch the HTTP server:
   ```bash
   python bot.py
   ```
   The server listens on port `8080` for incoming join requests.

2. **Join Room API Endpoint:**
   - **Endpoint:** `POST /join-room`
   - **Payload Example:**
     ```json
     {
       "roomName": "your-room-name"
     }
     ```
   - **Expected Response:**
     ```json
     {
       "success": true,
       "message": "Bot joining room your-room-name"
     }
     ```

## How It Works

- **Bot Token Generation:**
  The bot token is created using LiveKit API credentials and is used to authenticate the connection to the specified room.

- **Voice Assistant Initialization:**
  After connecting to a room, the bot sets up:
  - A chat context with a detailed persona and conversational guidelines.
  - Plugins for STT (using Deepgram), TTS (using OpenAI’s adapter), and VAD (using Silero).
  - Handlers for incoming chat messages to generate appropriate responses.
  
- **Email Functions:**
  - **send_email:** Validates email addresses and sends an email using SMTP.
  - **read_latest_email_subjects:** Connects to an IMAP server, retrieves recent email subjects, and returns them as a comma-separated list.

## Logging

The application logs key events such as token generation, room connection status, incoming messages, and email operations. Logs are output to the console for debugging and monitoring.


