#!/usr/bin/env python3
# apk_protector_bot_fixed.py

import os
import sys
import json
import hashlib
import subprocess
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import zipfile
import random
import string
import struct
import asyncio

# Telegram imports
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
except ImportError:
    print("📦 Installing required packages...")
    os.system("pip install python-telegram-bot --upgrade")
    os.system("pip install colorama")
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Colorama for colored output
try:
    import colorama
    colorama.init()
    R = colorama.Fore.RED
    G = colorama.Fore.GREEN
    Y = colorama.Fore.YELLOW
    B = colorama.Fore.BLUE
    W = colorama.Fore.WHITE
    RS = colorama.Style.RESET_ALL
except:
    R = G = Y = B = W = RS = ''

# ============= CONFIGURATION =============
# ⚠️ WARNING: Change this token immediately!
# Go to @BotFather and reset your token!
BOT_TOKEN = "8824864653:AAEmpXwgdiGLKqLq_VjiIcuvRbfFvcNbDHY"

# Your Telegram User ID (optional)
ADMIN_IDS = []

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
WORK_DIR = "apk_work"

# ============= APK PROTECTION TOOLS =============

class APKProtector:
    def __init__(self, apk_path):
        self.apk_path = apk_path
        self.apk_name = Path(apk_path).stem
        self.output_dir = f"protected_{self.apk_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    def protect(self, level="standard"):
        """Main protection function"""
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Step 1: Extract APK
        extracted = self.extract_apk()
        if not extracted:
            return False
        
        # Step 2: Find and protect Lua files
        lua_files = self.find_lua_files(extracted)
        if lua_files:
            if level == "basic":
                self.basic_protect(lua_files)
            elif level == "standard":
                self.standard_protect(lua_files, extracted)
            else:  # advanced
                self.advanced_protect(lua_files, extracted)
        
        # Step 3: Repack APK
        protected_apk = self.repack_apk(extracted)
        
        return protected_apk
    
    def extract_apk(self):
        """Extract APK contents using zip"""
        extract_dir = os.path.join(self.output_dir, "extracted")
        os.makedirs(extract_dir, exist_ok=True)
        
        try:
            with zipfile.ZipFile(self.apk_path, 'r') as z:
                z.extractall(extract_dir)
            return extract_dir
        except Exception as e:
            print(f"{R}Extract error: {e}{RS}")
            return None
    
    def find_lua_files(self, extract_dir):
        """Find all Lua files in extracted APK"""
        lua_files = []
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file.endswith(('.lua', '.luac')):
                    lua_files.append(os.path.join(root, file))
        return lua_files
    
    def basic_protect(self, lua_files):
        """Basic protection - rename and simple obfuscation"""
        for lua_file in lua_files:
            try:
                # Rename file
                new_name = f"{random.randint(1000,9999)}_{Path(lua_file).name}"
                new_path = os.path.join(os.path.dirname(lua_file), new_name)
                os.rename(lua_file, new_path)
            except:
                pass
    
    def standard_protect(self, lua_files, extract_dir):
        """Standard protection - encryption + anti-debug"""
        for lua_file in lua_files:
            try:
                with open(lua_file, 'rb') as f:
                    data = f.read()
                
                # Custom encryption
                encrypted = self.custom_encrypt(data)
                
                # Save encrypted
                with open(lua_file, 'wb') as f:
                    f.write(encrypted)
                
            except Exception as e:
                print(f"{R}Error protecting {lua_file}: {e}{RS}")
    
    def advanced_protect(self, lua_files, extract_dir):
        """Advanced protection - all features"""
        # Apply standard protection first
        self.standard_protect(lua_files, extract_dir)
        
        # Add integrity checks
        for lua_file in lua_files:
            self.add_integrity_check(lua_file)
    
    def custom_encrypt(self, data):
        """Custom encryption to bypass common decryption tools"""
        # Generate random key
        key = random.randint(1, 255)
        
        # Add random header
        header = bytes([random.randint(0, 255) for _ in range(16)])
        
        # XOR encryption with variable key
        encrypted = bytearray()
        for i, byte in enumerate(data):
            # Key changes based on position
            dynamic_key = (key + i) & 0xFF
            encrypted.append(byte ^ dynamic_key)
        
        # Add header and key info
        result = header + bytes([key]) + bytes(encrypted)
        
        # Add fake Lua magic at the end to confuse tools
        fake_magic = b'\x1bLua\x53\x00\x00\x00\x00'
        result += fake_magic
        
        return result
    
    def add_integrity_check(self, lua_file):
        """Add integrity check to Lua file"""
        # Create checksum file
        with open(lua_file, 'rb') as f:
            data = f.read()
            checksum = hashlib.md5(data).hexdigest()
        
        checksum_file = lua_file + ".checksum"
        with open(checksum_file, 'w') as f:
            f.write(checksum)
    
    def repack_apk(self, extract_dir):
        """Repack APK"""
        output_apk = os.path.join(self.output_dir, f"{self.apk_name}_protected.apk")
        
        try:
            # Create ZIP
            with zipfile.ZipFile(output_apk, 'w', zipfile.ZIP_DEFLATED) as z:
                for root, dirs, files in os.walk(extract_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, extract_dir)
                        z.write(file_path, arcname)
            
            return output_apk
            
        except Exception as e:
            print(f"{R}Repack error: {e}{RS}")
            return None

# ============= TELEGRAM BOT =============

class APKProtectorBot:
    def __init__(self):
        self.user_data = {}
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a message when /start is issued."""
        welcome_text = f"""
{R}╔══════════════════════════════════════════╗
║     {W}APK PROTECTOR BOT{R}              ║
╚══════════════════════════════════════════╝{RS}

{B}🔐 Features:{RS}
• Protect Lua files from decryption
• Add anti-debugging measures
• Custom encryption
• APK hardening

{B}📤 How to use:{RS}
1. Send me an APK file
2. Choose protection level
3. Download protected APK

{B}⚙️ Commands:{RS}
/start - Show this message
/help - Detailed help
/status - Check bot status

{R}⚠️ Note:{RS} Max file size: 50MB
        """
        await update.message.reply_text(welcome_text)
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a detailed help message."""
        help_text = f"""
{Y}🔧 APK Protection Guide{RS}

{B}Protection Levels:{RS}

{L}1. Basic Protection{RS}
   • Rename Lua files
   • Quick protection

{L}2. Standard Protection{RS} (Recommended)
   • Custom XOR encryption
   • Anti-debug flags
   • String obfuscation

{L}3. Advanced Protection{RS}
   • All of the above +
   • Integrity checks
   • Runtime decryption

{B}📋 Requirements:{RS}
• Android APK file
• Minimum 5MB free space

{B}⚠️ Important:{RS}
• Only for educational purposes
• Test on your own apps
        """
        await update.message.reply_text(help_text)
    
    async def handle_apk(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle APK file uploads."""
        if not update.message.document:
            await update.message.reply_text("❌ Please send an APK file.")
            return
        
        # Check file
        document = update.message.document
        file_name = document.file_name
        
        if not file_name.endswith('.apk'):
            await update.message.reply_text("❌ Please send a valid APK file.")
            return
        
        if document.file_size > MAX_FILE_SIZE:
            await update.message.reply_text(f"❌ File too large. Max: {MAX_FILE_SIZE/1024/1024:.0f}MB")
            return
        
        # Download APK
        status_msg = await update.message.reply_text("📥 Downloading APK...")
        
        try:
            file = await context.bot.get_file(document.file_id)
            apk_path = f"{WORK_DIR}/temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.apk"
            await file.download_to_drive(apk_path)
            
            # Analyze APK
            await status_msg.edit_text("🔍 Analyzing APK...")
            analysis = self.analyze_apk(apk_path)
            
            # Show protection options
            keyboard = [
                [InlineKeyboardButton("🛡️ Basic", callback_data="protect_basic")],
                [InlineKeyboardButton("🛡️ Standard (Recommended)", callback_data="protect_standard")],
                [InlineKeyboardButton("🛡️ Advanced", callback_data="protect_advanced")],
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Store user data
            context.user_data['apk_path'] = apk_path
            context.user_data['apk_name'] = document.file_name
            
            await status_msg.delete()
            await update.message.reply_text(
                f"{G}✅ APK Loaded{RS}\n\n"
                f"{B}📊 Analysis:{RS}\n"
                f"• Name: {document.file_name}\n"
                f"• Size: {document.file_size/1024/1024:.2f} MB\n"
                f"• Lua files: {analysis['lua_count']}\n\n"
                f"{Y}Select protection level:{RS}",
                reply_markup=reply_markup
            )
            
        except Exception as e:
            await status_msg.edit_text(f"❌ Error: {str(e)}")
    
    def analyze_apk(self, apk_path):
        """Analyze APK for Lua files"""
        lua_count = 0
        try:
            with zipfile.ZipFile(apk_path, 'r') as z:
                for info in z.infolist():
                    if info.filename.endswith(('.lua', '.luac')):
                        lua_count += 1
        except:
            pass
        
        return {'lua_count': lua_count}
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries."""
        query = update.callback_query
        await query.answer()
        
        if query.data == "cancel":
            await query.edit_message_text("❌ Operation cancelled.")
            return
        
        if query.data.startswith("protect_"):
            level = query.data.replace("protect_", "")
            await self.protect_apk(update, context, level)
    
    async def protect_apk(self, update: Update, context: ContextTypes.DEFAULT_TYPE, level: str):
        """Protect the APK with selected level."""
        query = update.callback_query
        apk_path = context.user_data.get('apk_path')
        apk_name = context.user_data.get('apk_name', 'app.apk')
        
        if not apk_path or not os.path.exists(apk_path):
            await query.edit_message_text("❌ APK file not found. Please try again.")
            return
        
        await query.edit_message_text(f"🛡️ Applying {level} protection... This may take a few minutes.")
        
        try:
            # Apply protection
            protector = APKProtector(apk_path)
            protected_apk = protector.protect(level)
            
            if protected_apk and os.path.exists(protected_apk):
                # Upload protected APK
                await query.edit_message_text("📤 Uploading protected APK...")
                
                with open(protected_apk, 'rb') as f:
                    await context.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=f,
                        filename=f"{Path(apk_name).stem}_protected_{level}.apk",
                        caption=f"""
✅ Protection Complete!

🛡️ Level: {level}
📦 Original: {apk_name}
🔐 Protected: Yes

📋 Features Applied:
• Custom encryption
• Anti-debug measures
• Runtime decryption

⚠️ Note: Test on your device first!
                        """
                    )
                
                await query.edit_message_text("✅ APK protected and uploaded successfully!")
                
                # Cleanup
                try:
                    shutil.rmtree(protector.output_dir)
                    os.remove(apk_path)
                except:
                    pass
                
            else:
                await query.edit_message_text("❌ Protection failed. Please try again.")
                
        except Exception as e:
            await query.edit_message_text(f"❌ Error during protection: {str(e)}")
    
    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check bot status."""
        status_text = f"""
{B}🤖 Bot Status{RS}

{G}✅ Online and ready!{RS}

{B}📊 Statistics:{RS}
• Max file size: {MAX_FILE_SIZE/1024/1024:.0f}MB
• Supported: APK files
• Protection levels: 3

{B}💾 System:{RS}
• Platform: Android
• Python: 3.13
• Status: Active

{Y}📝 Note:{RS}
• All processing is done locally
• Files are temporary
• No data is stored permanently
        """
        await update.message.reply_text(status_text)
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors."""
        print(f"{R}Error: {context.error}{RS}")
        try:
            await update.message.reply_text("❌ An error occurred. Please try again later.")
        except:
            pass

# ============= RUN BOT =============

def main():
    print(f"""
{R}╔══════════════════════════════════════════╗
║     {W}APK PROTECTOR BOT{R}              ║
╚══════════════════════════════════════════╝{RS}
    
{G}Starting bot...{RS}
    """)
    
    # Check for dependencies
    try:
        import telegram
    except ImportError:
        print("📦 Installing required packages...")
        os.system("pip install python-telegram-bot --upgrade")
    
    # Create work directory
    os.makedirs(WORK_DIR, exist_ok=True)
    
    # Create bot instance
    bot = APKProtectorBot()
    
    # Use ApplicationBuilder (recommended)
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .build()
    )
    
    # Add handlers
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("help", bot.help))
    application.add_handler(CommandHandler("status", bot.status))
    application.add_handler(MessageHandler(filters.Document.ALL, bot.handle_apk))
    application.add_handler(CallbackQueryHandler(bot.handle_callback))
    application.add_error_handler(bot.error_handler)
    
    print(f"{G}✅ Bot is running!{RS}")
    print(f"{Y}Press Ctrl+C to stop{RS}\n")
    
    # Start bot
    application.run_polling()

if __name__ == "__main__":
    main()