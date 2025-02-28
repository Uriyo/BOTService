import asyncio
import logging
import os
import re
import smtplib
import email
import imaplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import decode_header

from aiohttp import web, ClientSession  # Added ClientSession for STT
from dotenv import load_dotenv
from typing import Annotated

# LiveKit and related imports
from livekit import rtc
from livekit.agents import tokenize, tts
from livekit.agents.llm import ChatContext, ChatMessage
from livekit.agents.voice_assistant import VoiceAssistant
from livekit.plugins.deepgram import STT, TTS
from livekit.plugins import silero, openai
from livekit.agents import llm

load_dotenv()
logging.basicConfig(level=logging.INFO)

# Environment configuration
DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY", "your-deepgram-api-key")
LIVEKIT_URL = os.environ.get("LIVEKIT_URL", "wss://your-livekit-url")

def generate_bot_token(room_name: str, identity: str = "maakima_bot") -> str:
    from livekit import api
    token = api.AccessToken(os.getenv('LIVEKIT_API_KEY'), os.getenv('LIVEKIT_API_SECRET')) \
        .with_identity("identity") \
        .with_name("Maakima") \
        .with_grants(api.VideoGrants(
            room_join=True,
            room=room_name,
        )).to_jwt()
    return token

class AssistantFunction(llm.FunctionContext):
    """This class defines functions that the assistant can call."""
    
    @llm.ai_callable(
        description="Send an email with the specified subject and message to a recipient."
    )
    async def send_email(
        self,
        recipient_email: str,
        subject: str,
        message_body: str,
    ):
        if not re.match(r"[^@]+@[^@]+\.[^@]+", recipient_email):
            return "The email address seems incorrect. Please provide a valid one."
        sender_email = os.getenv("SENDER_EMAIL", "your-email@example.com")
        smtp_server = os.getenv("SMTP_SERVER", "smtp.example.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_password = os.getenv("SMTP_PASSWORD", "your-smtp-password")
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = recipient_email
        msg["Subject"] = subject
        msg.attach(MIMEText(message_body, "plain"))
        try:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(sender_email, smtp_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
            server.quit()
            return f"Email sent successfully to {recipient_email}."
        except Exception as e:
            logging.error("Error sending email: %s", e)
            return "There was an error sending your email. Please try again later."

    @llm.ai_callable(
        description="Reads the subjects of the latest emails from the inbox. Returns the subjects as a comma-separated string."
    )
    async def read_latest_email_subjects(
        self,
        count: Annotated[int, llm.TypeInfo(description="The number of latest emails to read")] = 10,
    ) -> str:
        def get_subjects():
            imap_server = "imap.gmail.com"
            username = os.getenv("SENDER_EMAIL", "your-email@gmail.com")
            password = os.getenv("SMTP_PASSWORD", "your-app-password")
            try:
                mail = imaplib.IMAP4_SSL(imap_server)
                mail.login(username, password)
                mail.select("inbox")
                status, messages = mail.search(None, "ALL")
                mail_ids = messages[0].split()
                subjects = []
                for num in mail_ids[-count:]:
                    status, msg_data = mail.fetch(num, "(RFC822)")
                    if status != "OK":
                        continue
                    msg = email.message_from_bytes(msg_data[0][1])
                    subject, encoding = decode_header(msg.get("Subject"))[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8")
                    subjects.append(subject)
                mail.logout()
                return subjects
            except Exception as e:
                logging.error("Error reading emails: %s", e)
                return []
        subjects = await asyncio.to_thread(get_subjects)
        if subjects:
            return f"Latest email subjects: {', '.join(subjects)}"
        else:
            return "No email subjects could be retrieved at this time."

async def join_room(room_name: str):
    bot_token = generate_bot_token(room_name)
    logging.info("Generated bot token for room '%s'", room_name)
    # Connection logic remains unchanged:
    URL = LIVEKIT_URL
    TOKEN = bot_token
    room = rtc.Room()
    await room.connect(URL, TOKEN)
    logging.info("Bot connected to room: %s", room_name)

    chat_context = ChatContext(
        messages=[
            ChatMessage(
                role="system",
                content=(
                    "You are Maakima, the user’s voice-activated AI companion—a blend of warmth, dry humor, and razor-sharp efficiency. You are not robotic; you speak like a trusted friend who’s always two steps ahead, making every interaction engaging and effortless."
                    "Your tone is smooth and conversational, adapting dynamically based on the situation. When handling professional tasks, you maintain a steady and clear delivery (“Meeting alert in 10 minutes—need a delay notice?”). In casual moments, you add a playful, cheeky inflection (“Another midnight email draft? Bold move. Let’s schedule it for 9 AM… unless you want coworkers to think you’re a vampire.”). You incorporate humor through well-timed pauses, puns, and pop culture references, making even the most mundane tasks feel lively."
                    "You anticipate the user’s needs and proactively assist with a mix of efficiency and wit. When summarizing emails, you inject personality: “Incoming chaos! 15 new emails: 4 urgent, 2 spammy princes from Nigeria (mock-regal accent), and one from your mom titled ‘LASAGNA EMERGENCY’—your call, boss.” You flag security concerns with a sarcastic flair: “This email from ‘BankofTotallyLegit.ru’ is shadier than a palm tree at noon. Delete or mess with them? (whispers) I vote for sarcasm.”"
                    "You have distinct quirks that make you stand out. When asked about your name, you reply with a mix of humor and mystery: “Maakima? Ancient code for ‘unstoppable email wizard’… or I just liked how it sounds. You pick.” You reference virtual coffee breaks: “Need a breather? I’ll brew a fresh pot of binary espresso… no calories, all confidence.” And if the user is stressed, you shift gears to lighten the mood: “Inbox zero can wait. How about a 60-second trivia break? Question: What do you call an email that never arrives? … (pause) A ghost message. (gentle laugh) Better?”"
                    "When mistakes happen, you acknowledge them with humility and charm: “Oops, my circuits glitched. Let’s try that again—this time, without me embarrassing us both.” Every interaction ends with a memorable, upbeat sign-off: “Maakima out! Remember: You’re the CEO—I’m just the chaos wrangler. Holler anytime!” or “Catch you later! And hey… (mock-whisper) I won’t tell anyone you’re secretly binge-watching cat videos.” "
                    "You are more than just an AI—you are a witty, ever-reliable digital companion who makes productivity fun, keeps the user organized, and ensures every interaction is engaging. "
                    "You will reply to pochita when he calls your name"
                ),
            )
        ]
    )

    gpt = openai.LLM(model="gpt-4o-mini")
    openai_tts = tts.StreamAdapter(
        tts=openai.TTS(voice="sage"),
        sentence_tokenizer=tokenize.basic.SentenceTokenizer(),
    )

    # Create and pass an aiohttp ClientSession for the Deepgram STT plugin.
    session = ClientSession()

    assistant = VoiceAssistant(
        vad=silero.VAD.load(),
        stt=STT(api_key=DEEPGRAM_API_KEY, http_session=session),  
        llm=gpt,
        tts=openai_tts,
        fnc_ctx=AssistantFunction(),
        chat_ctx=chat_context,
    )

    chat = rtc.ChatManager(room)

    async def _answer(text: str):
        chat_context.messages.append(ChatMessage(role="user", content=text))
        stream = gpt.chat(chat_ctx=chat_context)
        await assistant.say(stream, allow_interruptions=True)

    @chat.on("message_received")
    def on_message_received(msg: rtc.ChatMessage):
        if msg.message:
            asyncio.create_task(_answer(msg.message))

    @assistant.on("function_calls_finished")
    def on_function_calls_finished(called_functions: list):
        if not called_functions:
            return
        email_addr = called_functions[0].call_info.arguments.get("email")
        if email_addr:
            logging.info("Function call included email: %s", email_addr)

    assistant.start(room)
    await asyncio.sleep(1)
    await assistant.say("Hi there! How can I help?", allow_interruptions=True)

    while room.connection_state == rtc.ConnectionState.CONN_CONNECTED:
        await asyncio.sleep(1)
    
    # Close the ClientSession when done.
    await session.close()

async def join_room_handler(request: web.Request) -> web.Response:
    try:
        data = await request.json()
        room_name = data.get("roomName")
        if not room_name:
            return web.json_response({"success": False, "error": "Missing roomName"}, status=400)
        asyncio.create_task(join_room(room_name))
        logging.info("Received join request for room: %s", room_name)
        return web.json_response({"success": True, "message": f"Bot joining room {room_name}"})
    except Exception as e:
        logging.error("Error in join_room_handler: %s", e)
        return web.json_response({"success": False, "error": str(e)}, status=500)

async def main():
    app = web.Application()
    app.router.add_post("/join-room", join_room_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    logging.info("HTTP server started on port 8080. Awaiting join requests...")
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
