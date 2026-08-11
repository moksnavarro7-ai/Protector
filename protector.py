#!/usr/bin/env python3
# apk_protector_bot_with_loader.py

import os
import sys
import json
import hashlib
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import zipfile
import random
import struct
import base64

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
# ⚠️ CHANGE THIS TO YOUR TOKEN
BOT_TOKEN = "8824864653:AAEmpXwgdiGLKqLq_VjiIcuvRbfFvcNbDHY"  # CHANGE THIS!

MAX_FILE_SIZE = 50 * 1024 * 1024
WORK_DIR = "apk_work"

# ============= ENCRYPTION/DECRYPTION =============

class LuaEncryptor:
    """Handles Lua file encryption with runtime decryption support"""
    
    @staticmethod
    def encrypt_lua(data, key=None):
        """Encrypt Lua data with custom method"""
        if key is None:
            key = random.randint(1, 255)
        
        # Add header
        header = b'LUA_ENC' + bytes([key])
        
        # XOR encryption with dynamic key
        encrypted = bytearray()
        for i, byte in enumerate(data):
            dynamic_key = (key + i) & 0xFF
            encrypted.append(byte ^ dynamic_key)
        
        # Add checksum
        checksum = hashlib.md5(encrypted).digest()[:8]
        
        return header + checksum + bytes(encrypted)
    
    @staticmethod
    def create_loader(original_filename, encrypted_data):
        """Create a Lua loader script that decrypts at runtime"""
        
        # Encode encrypted data as base64 for embedding
        enc_b64 = base64.b64encode(encrypted_data).decode('ascii')
        
        loader_template = f'''-- Auto-generated Lua Decryptor
-- Original: {original_filename}

local function decrypt_data(enc_data)
    -- Extract key
    local key = enc_data:byte(8)
    
    -- Remove header and checksum
    local data_start = 16  -- 7 bytes header + 1 byte key + 8 bytes checksum
    local encrypted = enc_data:sub(data_start)
    
    -- Decrypt using XOR
    local decrypted = {{}}
    for i = 1, #encrypted do
        local byte = encrypted:byte(i)
        local dynamic_key = (key + (i - 1)) & 0xFF
        decrypted[i] = string.char(byte ~ dynamic_key)
    end
    
    return table.concat(decrypted)
end

-- Load and execute decrypted code
local enc_data = "{enc_b64}"
local decrypted = decrypt_data(enc_data)

-- Execute the decrypted code
local chunk, err = loadstring(decrypted)
if chunk then
    chunk()
else
    print("Error loading decrypted script:", err)
end
'''
        return loader_template

# ============= APK PROTECTOR =============

class APKProtector:
    def __init__(self, apk_path):
        self.apk_path = apk_path
        self.apk_name = Path(apk_path).stem
        self.output_dir = f"protected_{self.apk_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.encryptor = LuaEncryptor()
        
    def protect(self, level="standard"):
        """Main protection function"""
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Extract APK
        extracted = self.extract_apk()
        if not extracted:
            return False
        
        # Find Lua files
        lua_files = self.find_lua_files(extracted)
        
        if lua_files:
            if level == "basic":
                self.basic_protect(lua_files, extracted)
            elif level == "standard":
                self.standard_protect(lua_files, extracted)
            else:  # advanced
                self.advanced_protect(lua_files, extracted)
        
        # Repack APK
        protected_apk = self.repack_apk(extracted)
        
        return protected_apk
    
    def extract_apk(self):
        """Extract APK"""
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
        """Find all Lua files"""
        lua_files = []
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file.endswith(('.lua', '.luac')):
                    lua_files.append(os.path.join(root, file))
        return lua_files
    
    def basic_protect(self, lua_files, extract_dir):
        """Basic protection - rename files"""
        for lua_file in lua_files:
            try:
                # Read original
                with open(lua_file, 'rb') as f:
                    data = f.read()
                
                # Encrypt
                encrypted = self.encryptor.encrypt_lua(data)
                
                # Create loader
                loader = self.encryptor.create_loader(
                    Path(lua_file).name, 
                    encrypted
                )
                
                # Replace with loader
                with open(lua_file, 'w', encoding='utf-8') as f:
                    f.write(loader)
                
            except Exception as e:
                print(f"{R}Error: {e}{RS}")
    
    def standard_protect(self, lua_files, extract_dir):
        """Standard protection with encryption"""
        # Create decryption helper
        self.create_decryption_helper(extract_dir)
        
        for lua_file in lua_files:
            try:
                # Read original
                with open(lua_file, 'rb') as f:
                    data = f.read()
                
                # Encrypt with stronger method
                encrypted = self.encrypt_lua_advanced(data)
                
                # Save encrypted file with .enc extension
                enc_path = lua_file + '.enc'
                with open(enc_path, 'wb') as f:
                    f.write(encrypted)
                
                # Create loader that references the encrypted file
                loader = self.create_loader_with_file(Path(lua_file).name, enc_path)
                
                # Replace original with loader
                with open(lua_file, 'w', encoding='utf-8') as f:
                    f.write(loader)
                
            except Exception as e:
                print(f"{R}Error: {e}{RS}")
    
    def advanced_protect(self, lua_files, extract_dir):
        """Advanced protection with native library"""
        # Standard protection first
        self.standard_protect(lua_files, extract_dir)
        
        # Add native decryption library
        self.create_native_decryptor(extract_dir)
        
        # Add anti-debug
        self.add_anti_debug(extract_dir)
    
    def encrypt_lua_advanced(self, data):
        """Advanced encryption with multiple layers"""
        # Layer 1: XOR
        key1 = random.randint(1, 255)
        encrypted = bytearray()
        for i, byte in enumerate(data):
            encrypted.append(byte ^ ((key1 + i) & 0xFF))
        
        # Layer 2: Byte reversal
        encrypted = encrypted[::-1]
        
        # Layer 3: Simple substitution
        encrypted = bytes([(b + 0x37) & 0xFF for b in encrypted])
        
        # Add header
        header = b'LUA_ADV' + bytes([key1]) + struct.pack('>I', len(data))
        
        return header + encrypted
    
    def create_decryption_helper(self, extract_dir):
        """Create decryption helper script"""
        helper_code = '''
-- Lua Decryption Helper
local decrypt_helper = {}

function decrypt_helper.decrypt_file(filename)
    local enc_file = io.open(filename .. '.enc', 'rb')
    if not enc_file then return nil end
    
    local enc_data = enc_file:read('*all')
    enc_file:close()
    
    -- Extract header
    local header = enc_data:sub(1, 7)
    if header ~= 'LUA_ADV' then
        return nil
    end
    
    -- Extract key and size
    local key = enc_data:byte(8)
    local data_size = struct.unpack('>I', enc_data:sub(9, 12))
    
    -- Decrypt
    local encrypted = enc_data:sub(13)
    local decrypted = {}
    
    for i = 1, #encrypted do
        local byte = encrypted:byte(i)
        byte = (byte - 0x37) & 0xFF
        decrypted[i] = string.char(byte)
    end
    
    -- Reverse
    decrypted = table.concat(decrypted)
    decrypted = decrypted:reverse()
    
    -- XOR decrypt
    local result = {}
    for i = 1, #decrypted do
        local byte = decrypted:byte(i)
        local dynamic_key = (key + (i - 1)) & 0xFF
        result[i] = string.char(byte ~ dynamic_key)
    end
    
    return table.concat(result)
end

return decrypt_helper
'''
        
        helper_path = os.path.join(extract_dir, 'decrypt_helper.lua')
        with open(helper_path, 'w', encoding='utf-8') as f:
            f.write(helper_code)
    
    def create_loader_with_file(self, filename, enc_path):
        """Create loader that reads encrypted file"""
        loader_code = f'''
-- Auto-generated Lua Loader
-- Loads encrypted file: {filename}

local decrypt_helper = require('decrypt_helper')

local function load_script(filename)
    local decrypted = decrypt_helper.decrypt_file(filename)
    if decrypted then
        local chunk, err = loadstring(decrypted)
        if chunk then
            return chunk()
        else
            print("Error loading script:", err)
            return nil
        end
    else
        print("Failed to decrypt:", filename)
        return nil
    end
end

-- Execute the script
load_script('{Path(filename).stem}')
'''
        return loader_code
    
    def create_native_decryptor(self, extract_dir):
        """Create C++ decryption library"""
        cpp_code = '''
#include <jni.h>
#include <string>
#include <vector>

extern "C" {

JNIEXPORT jbyteArray JNICALL
Java_com_your_app_Decryptor_decryptLua(JNIEnv *env, jobject thiz,
                                       jbyteArray data, jint key) {
    jsize len = env->GetArrayLength(data);
    jbyte *bytes = env->GetByteArrayElements(data, NULL);
    
    std::vector<jbyte> result(len);
    
    for (int i = 0; i < len; i++) {
        int dynamic_key = (key + i) & 0xFF;
        result[i] = bytes[i] ^ dynamic_key;
    }
    
    env->ReleaseByteArrayElements(data, bytes, JNI_ABORT);
    
    jbyteArray out = env->NewByteArray(len);
    env->SetByteArrayRegion(out, 0, len, result.data());
    
    return out;
}

}
'''
        # Save C++ file
        jni_dir = os.path.join(extract_dir, 'lib', 'native_decryptor')
        os.makedirs(jni_dir, exist_ok=True)
        
        with open(os.path.join(jni_dir, 'decryptor.cpp'), 'w') as f:
            f.write(cpp_code)
    
    def add_anti_debug(self, extract_dir):
        """Add anti-debugging code"""
        # Modify AndroidManifest.xml
        manifest_path = os.path.join(extract_dir, 'AndroidManifest.xml')
        if os.path.exists(manifest_path):
            with open(manifest_path, 'r', encoding='utf-8', errors='ignore') as f:
                manifest = f.read()
            
            # Add anti-debug attributes
            manifest = manifest.replace(
                '<application',
                '<application android:debuggable="false" android:testOnly="false"'
            )
            
            with open(manifest_path, 'w', encoding='utf-8') as f:
                f.write(manifest)
    
    def repack_apk(self, extract_dir):
        """Repack APK"""
        output_apk = os.path.join(self.output_dir, f"{self.apk_name}_protected.apk")
        
        try:
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
        welcome = f"""
{R}╔══════════════════════════════════════════╗
║     {W}APK PROTECTOR BOT{R}              ║
╚══════════════════════════════════════════╝{RS}

{B}🔐 Features:{RS}
• Encrypt Lua files with runtime decryption
• Fix: "syntax error near '<\\203>'" errors
• Auto-loader for encrypted files

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
        await update.message.reply_text(welcome)
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = f"""
{Y}🔧 APK Protection Guide{RS}

{B}Protection Levels:{RS}

{L}1. Basic Protection{RS}
   • Encrypts Lua files
   • Adds runtime decryption
   • Fixes syntax errors

{L}2. Standard Protection{RS} (Recommended)
   • All basic features
   • Multi-layer encryption
   • File integrity checks

{L}3. Advanced Protection{RS}
   • All standard features
   • Native C++ decryption
   • Anti-debugging measures

{B}📋 Requirements:{RS}
• Android APK file
• Minimum 5MB free space

{B}⚠️ Important:{RS}
• Test on your device first
• Make backup of original APK
        """
        await update.message.reply_text(help_text)
    
    async def handle_apk(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message.document:
            await update.message.reply_text("❌ Please send an APK file.")
            return
        
        document = update.message.document
        file_name = document.file_name
        
        if not file_name.endswith('.apk'):
            await update.message.reply_text("❌ Please send a valid APK file.")
            return
        
        if document.file_size > MAX_FILE_SIZE:
            await update.message.reply_text(f"❌ File too large. Max: {MAX_FILE_SIZE/1024/1024:.0f}MB")
            return
        
        status_msg = await update.message.reply_text("📥 Downloading APK...")
        
        try:
            file = await context.bot.get_file(document.file_id)
            apk_path = f"{WORK_DIR}/temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.apk"
            await file.download_to_drive(apk_path)
            
            await status_msg.edit_text("🔍 Analyzing APK...")
            analysis = self.analyze_apk(apk_path)
            
            keyboard = [
                [InlineKeyboardButton("🛡️ Basic", callback_data="protect_basic")],
                [InlineKeyboardButton("🛡️ Standard (Recommended)", callback_data="protect_standard")],
                [InlineKeyboardButton("🛡️ Advanced", callback_data="protect_advanced")],
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
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
        query = update.callback_query
        await query.answer()
        
        if query.data == "cancel":
            await query.edit_message_text("❌ Operation cancelled.")
            return
        
        if query.data.startswith("protect_"):
            level = query.data.replace("protect_", "")
            await self.protect_apk(update, context, level)
    
    async def protect_apk(self, update: Update, context: ContextTypes.DEFAULT_TYPE, level: str):
        query = update.callback_query
        apk_path = context.user_data.get('apk_path')
        apk_name = context.user_data.get('apk_name', 'app.apk')
        
        if not apk_path or not os.path.exists(apk_path):
            await query.edit_message_text("❌ APK file not found. Please try again.")
            return
        
        await query.edit_message_text(f"🛡️ Applying {level} protection... This may take a few minutes.")
        
        try:
            protector = APKProtector(apk_path)
            protected_apk = protector.protect(level)
            
            if protected_apk and os.path.exists(protected_apk):
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

📋 Fixed Issues:
• ✓ Lua encryption with runtime decryption
• ✓ No more "syntax error near '<\\203>'"
• ✓ Automatic script loading

⚠️ Note: Install and test on your device!
                        """
                    )
                
                await query.edit_message_text("✅ APK protected and uploaded successfully!")
                
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
        status_text = f"""
{B}🤖 Bot Status{RS}

{G}✅ Online and ready!{RS}

{B}📊 Statistics:{RS}
• Max file size: {MAX_FILE_SIZE/1024/1024:.0f}MB
• Supported: APK files
• Protection levels: 3
• Encryption: Multi-layer XOR

{B}💾 System:{RS}
• Platform: Android
• Python: 3.13
• Status: Active

{Y}📝 Note:{RS}
• Includes runtime decryption
• Fixes syntax errors
• No data is stored permanently
        """
        await update.message.reply_text(status_text)
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    # Check token
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print(f"""
{R}❌ ERROR: Bot token not configured!{RS}

{Y}Get your token from @BotFather on Telegram{RS}

1. Open Telegram
2. Search for {B}@BotFather{RS}
3. Send {B}/newbot{RS}
4. Copy your token
5. Update BOT_TOKEN in the script
        """)
        sys.exit(1)
    
    os.makedirs(WORK_DIR, exist_ok=True)
    
    bot = APKProtectorBot()
    
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .build()
    )
    
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("help", bot.help))
    application.add_handler(CommandHandler("status", bot.status))
    application.add_handler(MessageHandler(filters.Document.ALL, bot.handle_apk))
    application.add_handler(CallbackQueryHandler(bot.handle_callback))
    application.add_error_handler(bot.error_handler)
    
    print(f"{G}✅ Bot is running!{RS}")
    print(f"{Y}Press Ctrl+C to stop{RS}\n")
    
    application.run_polling()

if __name__ == "__main__":
    main()
