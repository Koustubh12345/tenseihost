import os
import asyncio
import time
import math
import json
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import psutil
import aiohttp
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google_auth_oauthlib.flow import InstalledAppFlow

# Environment variables
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")
GDRIVE_FOLDER_ID = os.getenv("GDRIVE_FOLDER_ID")
ADMINS = [int(x) for x in os.getenv("ADMINS").split()]
BASE_URL = os.getenv("BASE_URL")

# Google OAuth credentials (from your provided JSON)
GOOGLE_CLIENT_ID = "96557220545-51eompa8epqef2fbo0t8810pisjnvcjt.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "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"
REDIRECT_URI = "https://tenseihost.onrender.com/auth"

# Initialize bot
app = Client(
    "mirror_bot",
    bot_token=BOT_TOKEN,
    api_id=API_ID,
    api_hash=API_HASH
)

# Google Drive credentials storage
TOKEN_FILE = "gdrive_token.json"

# Create OAuth flow
def create_oauth_flow():
    return InstalledAppFlow.from_client_config(
        client_config={
            "installed": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI]
            }
        },
        scopes=["https://www.googleapis.com/auth/drive"],
        redirect_uri=REDIRECT_URI
    )

# Get Google Drive service
def get_gdrive_service():
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE)
        if creds.valid and creds.expiry and creds.expiry > datetime.now():
            return build("drive", "v3", credentials=creds)
    
    return None

# Save credentials
def save_credentials(creds):
    with open(TOKEN_FILE, 'w') as token:
        token.write(creds.to_json())

# Progress bar formatting
def progress_bar(current, total):
    percentage = current / total
    progress = math.floor(percentage * 10)
    bar = "⟦ "
    for i in range(10):
        if i < progress:
            bar += "▰ "
        else:
            bar += "▱ "
    bar += "⟧"
    return bar, f"{percentage * 100:.1f}%"

# Format bytes to human readable
def format_bytes(bytes):
    if bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(bytes, 1024)))
    p = math.pow(1024, i)
    s = round(bytes / p, 2)
    return f"{s}{size_name[i]}"

# Get system stats
def get_system_stats():
    cpu = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    net = psutil.net_io_counters()
    
    return {
        "cpu": f"{cpu:.1f}%",
        "ram": f"{mem.percent:.1f}%",
        "disk_free": f"{format_bytes(disk.free)} ({disk.free/disk.total*100:.1f}%)",
        "dl_speed": f"{format_bytes(net.bytes_recv)}/s",
        "ul_speed": f"{format_bytes(net.bytes_sent)}/s"
    }

# Download with progress tracking
async def download_file(url, path, message):
    start_time = time.time()
    last_update = 0
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            total = int(response.headers.get('Content-Length', 0))
            current = 0
            
            with open(path, 'wb') as f:
                async for chunk in response.content.iter_chunked(1024):
                    f.write(chunk)
                    current += len(chunk)
                    
                    # Update progress every 2 seconds
                    if time.time() - last_update > 2:
                        elapsed = time.time() - start_time
                        speed = current / elapsed if elapsed > 0 else 0
                        eta = (total - current) / speed if speed > 0 else 0
                        
                        bar, percent = progress_bar(current, total)
                        stats = get_system_stats()
                        
                        text = f"""
📦 {os.path.basename(path)}
{bar}  {percent}
{format_bytes(current)} / {format_bytes(total)}  •  ⇣ {format_bytes(speed)}/s
ETA: {time.strftime('%Mm%Ss', time.gmtime(eta))}  •  Elapsed: {time.strftime('%Mm%Ss', time.gmtime(elapsed))}
⌬ Downloading  •  ⚙ PyroMulti v2.0.106
#GDrive  •  #Tg
👤 {message.from_user.first_name} | ID: {message.from_user.id}
⚡ Bot Stats
CPU: {stats['cpu']}  •  RAM: {stats['ram']}
Free: {stats['disk_free']}
DL: {stats['dl_speed']}  •  UL: {stats['ul_speed']}
"""
                        try:
                            await message.edit(text)
                            last_update = time.time()
                        except:
                            pass
    
    return path

# Upload to Telegram with progress
async def upload_to_telegram(client, path, message):
    start_time = time.time()
    last_update = 0
    
    def progress(current, total):
        nonlocal last_update
        if time.time() - last_update > 2:
            elapsed = time.time() - start_time
            speed = current / elapsed if elapsed > 0 else 0
            eta = (total - current) / speed if speed > 0 else 0
            
            bar, percent = progress_bar(current, total)
            stats = get_system_stats()
            
            text = f"""
📦 {os.path.basename(path)}
{bar}  {percent}
{format_bytes(current)} / {format_bytes(total)}  •  ⇡ {format_bytes(speed)}/s
ETA: {time.strftime('%Mm%Ss', time.gmtime(eta))}  •  Elapsed: {time.strftime('%Mm%Ss', time.gmtime(elapsed))}
⌬ Uploading  •  ⚙ PyroMulti v2.0.106
#GDrive  •  #Tg
👤 {message.from_user.first_name} | ID: {message.from_user.id}
⚡ Bot Stats
CPU: {stats['cpu']}  •  RAM: {stats['ram']}
Free: {stats['disk_free']}
DL: {stats['dl_speed']}  •  UL: {stats['ul_speed']}
"""
            asyncio.create_task(message.edit(text))
            last_update = time.time()
    
    await client.send_document(
        chat_id=message.chat.id,
        document=path,
        progress=progress
    )
    
    return path

# Upload to Google Drive
async def upload_to_gdrive(path, message):
    service = get_gdrive_service()
    if not service:
        await message.edit("❌ Google Drive not authorized. Use /auth to authorize.")
        return None
    
    file_metadata = {
        'name': os.path.basename(path),
        'parents': [GDRIVE_FOLDER_ID]
    }
    
    media = MediaIoBaseUpload(
        open(path, 'rb'),
        resumable=True
    )
    
    request = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    )
    
    response = None
    start_time = time.time()
    last_update = 0
    
    while response is None:
        status, response = request.next_chunk()
        if status:
            current = status.resumable_progress
            total = status.total_size
            elapsed = time.time() - start_time
            speed = current / elapsed if elapsed > 0 else 0
            eta = (total - current) / speed if speed > 0 else 0
            
            bar, percent = progress_bar(current, total)
            stats = get_system_stats()
            
            text = f"""
📦 {os.path.basename(path)}
{bar}  {percent}
{format_bytes(current)} / {format_bytes(total)}  •  ⇡ {format_bytes(speed)}/s
ETA: {time.strftime('%Mm%Ss', time.gmtime(eta))}  •  Elapsed: {time.strftime('%Mm%Ss', time.gmtime(elapsed))}
⌬ Uploading to GDrive  •  ⚙ PyroMulti v2.0.106
#GDrive  •  #Tg
👤 {message.from_user.first_name} | ID: {message.from_user.id}
⚡ Bot Stats
CPU: {stats['cpu']}  •  RAM: {stats['ram']}
Free: {stats['disk_free']}
DL: {stats['dl_speed']}  •  UL: {stats['ul_speed']}
"""
            if time.time() - last_update > 2:
                await message.edit(text)
                last_update = time.time()
    
    return f"https://drive.google.com/file/d/{response.get('id')}/view"

# Start command with GIF
@app.on_message(filters.command(["start"]))
async def start_command(client, message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📥 Mirror to Telegram", callback_data="mirror_tg")],
        [InlineKeyboardButton("☁️ Mirror to GDrive", callback_data="mirror_gdrive")],
        [InlineKeyboardButton("🔐 Authorize GDrive", callback_data="auth_gdrive")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
    ])
    
    await message.reply_animation(
        "https://c.tenor.com/25ykirk3P4YAAAAd/tenor.gif",
        caption=f"**Welcome to {BOT_USERNAME}!**\n\nI can mirror files from direct links to Telegram or Google Drive with real-time progress tracking.",
        reply_markup=keyboard
    )

# Auth command
@app.on_message(filters.command(["auth"]) & filters.user(ADMINS))
async def auth_command(client, message):
    flow = create_oauth_flow()
    auth_url, _ = flow.authorization_url(access_type='offline', prompt='consent')
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔐 Authorize Google Drive", url=auth_url)]
    ])
    
    await message.reply(
        "Click the button below to authorize Google Drive access:\n\n"
        "1. Click the button and grant permissions\n"
        "2. Copy the authorization code from the redirect URL\n"
        "3. Send it to me with /token <code>",
        reply_markup=keyboard
    )

# Token command
@app.on_message(filters.command(["token"]) & filters.user(ADMINS))
async def token_command(client, message):
    if len(message.command) < 2:
        return await message.reply("Please provide the authorization code: /token <code>")
    
    code = message.command[1]
    flow = create_oauth_flow()
    
    try:
        flow.fetch_token(code=code)
        creds = flow.credentials
        save_credentials(creds)
        await message.reply("✅ Google Drive authorized successfully!")
    except Exception as e:
        await message.reply(f"❌ Authorization failed: {str(e)}")

# Mirror command handler
@app.on_message(filters.command(["mirror"]))
async def mirror_command(client, message):
    if len(message.command) < 2:
        return await message.reply("Please provide a direct download link after /mirror")
    
    url = message.command[1]
    status = await message.reply("⏳ Starting download...")
    
    try:
        # Download file
        file_path = await download_file(url, f"downloads/{int(time.time())}_{os.path.basename(url)}", status)
        
        # Ask for destination
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Upload to Telegram", callback_data=f"upload_tg:{file_path}")],
            [InlineKeyboardButton("☁️ Upload to GDrive", callback_data=f"upload_gdrive:{file_path}")]
        ])
        await status.edit("✅ Download completed! Choose destination:", reply_markup=keyboard)
        
    except Exception as e:
        await status.edit(f"❌ Error: {str(e)}")

# Callback handler
@app.on_callback_query()
async def callback_handler(client, callback_query):
    data = callback_query.data
    
    if data == "mirror_tg":
        await callback_query.message.edit("Send me a direct download link with /mirror <url>")
    
    elif data == "mirror_gdrive":
        await callback_query.message.edit("Send me a direct download link with /mirror <url>")
    
    elif data == "auth_gdrive":
        flow = create_oauth_flow()
        auth_url, _ = flow.authorization_url(access_type='offline', prompt='consent')
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔐 Authorize Google Drive", url=auth_url)]
        ])
        
        await callback_query.message.edit(
            "Click the button below to authorize Google Drive access:\n\n"
            "1. Click the button and grant permissions\n"
            "2. Copy the authorization code from the redirect URL\n"
            "3. Send it to me with /token <code>",
            reply_markup=keyboard
        )
    
    elif data == "help":
        help_text = """
**How to use me:**

1. Send a direct download link with /mirror <url>
2. I'll download the file with real-time progress
3. Choose to upload to Telegram or Google Drive

**Features:**
- Real-time download/upload progress
- System statistics display
- Animated progress bars
- Google Drive integration
- Telegram file hosting

**Admin Commands:**
/auth - Authorize Google Drive
/token <code> - Complete authorization
        """
        await callback_query.message.edit(help_text)
    
    elif data.startswith("upload_tg:"):
        file_path = data.split(":", 1)[1]
        await callback_query.message.edit("⏳ Uploading to Telegram...")
        try:
            await upload_to_telegram(client, file_path, callback_query.message)
            await callback_query.message.edit("✅ Successfully uploaded to Telegram!")
            os.remove(file_path)
        except Exception as e:
            await callback_query.message.edit(f"❌ Upload failed: {str(e)}")
    
    elif data.startswith("upload_gdrive:"):
        file_path = data.split(":", 1)[1]
        await callback_query.message.edit("⏳ Uploading to Google Drive...")
        try:
            link = await upload_to_gdrive(file_path, callback_query.message)
            if link:
                await callback_query.message.edit(f"✅ Successfully uploaded to Google Drive!\n\n{link}")
                os.remove(file_path)
        except Exception as e:
            await callback_query.message.edit(f"❌ Upload failed: {str(e)}")

# Create downloads directory
os.makedirs("downloads", exist_ok=True)

# Start bot
print("Bot started...")
app.run()
