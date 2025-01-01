import os
import re
import time
from dotenv import find_dotenv, load_dotenv
from telegram.ext import Application, CommandHandler
from telethon import TelegramClient
import logging
import asyncio
import sys
import nest_asyncio
from collections import defaultdict
from flask import Flask, request  # Import Flask
import threading  # Import threading for running Flask in a separate thread
#from keep_alive import keep_alive
from telegram import Chat

#{os.getenv('RENDER_EXTERNAL_URL', '')}
#PORT = int(os.getenv("PORT", 8000))

#keep_alive()

nest_asyncio.apply()
WEBHOOK_URL = "https://multiplebuytrackers-a9hc.onrender.com"  # Use Render's external URL

# Telegram bot configuration
dotenv_path = find_dotenv()
load_dotenv(dotenv_path)
PORT = 10000
# Telethon client configuration
BOT_TOKEN = "7951730271:AAH1i5RbbJgWZ-QDGcLVBOl0tuZPJiJKOyc"
API_ID = 21202746#int(os.getenv("API_ID"))
API_HASH = "e700432294937e6925a83149ee7165a0"#os.getenv("API_HASH")




# Create Telethon client
async def initialize_telethon():
    global telethon_client
    telethon_client = TelegramClient('test', API_ID, API_HASH)
    await telethon_client.start()
    #logging.info("Telethon client initialized and started")

# Authorized users and groups (store without @ symbol)
AUTHORIZED_USERS = {'orehub1378', 'Kemoo1975', 'jeremi1234', 'Busiiiiii'}
AUTHORIZED_GROUPS = {"thetrackss"}

# Add a dictionary to store the last processed message IDs for each chat
last_processed_messages = defaultdict(set)
# Flag to control continuous scraping
continue_scraping = True

async def check_authorization(update):
    """Check if the user/group is authorized to use the bot"""
    chat_id = update.effective_chat.id
    user_username = update.effective_user.username
    chat_username = update.effective_chat.username
    if chat_id == -1002272071296:
        return True
    
    #if update.effective_chat.type == 'private':
        #return user_username and user_username.lower() in {user.lower() for user in AUTHORIZED_USERS}
    
    #return chat_username and chat_username.lower() in {group.lower() for group in AUTHORIZED_GROUPS}

def extract_pump_type(text):
    """Extract the pump type (Raydium/Pumpfun/Pump/Jupiter) from the message"""
    text_lower = text.lower()
    
    if 'raydium' in text_lower:
        return 'Raydium'
    elif 'pumpfun' in text_lower:
        return 'Pumpfun'
    elif 'jupiter' in text_lower:
        return 'Jupiter'
    elif 'pump' in text_lower:
        return 'Pump'
    return 'Unknown'  # Default value if no specific type is found

def is_trader_message(text):
    """Check if the message contains 'TRADER' and additional specified terms with conditions for 'buy' before 'sell'."""
    text_lower = text.lower()
    pump_keywords = ['pump', 'raydium', 'pumpfun', 'jupiter']
    contains_trader = 'trader' in text_lower
    buy_index = text_lower.find("buy")
    sell_index = text_lower.find("sell")
    contains_pump_keywords = any(keyword in text_lower for keyword in pump_keywords)

    if contains_trader and contains_pump_keywords and buy_index != -1 and (sell_index == -1 or buy_index < sell_index):
        return True
    return False

def extract_trader_name(text):
    """Extract the trader's name as an alphanumeric string from the text"""
    match = re.search(r'\bTRADER(\w+)', text, re.IGNORECASE)
    if match:
        return match.group(1)
    return "Unknown"

def extract_solana_address_and_amount(text):
    """Extract all Solana addresses and return the third one, if available."""
   
    amount_pattern = r'(\b\d+(\.\d{1,8})?\s+SOL\b)'

    # Extract all Solana addresses
    matches = re.findall(r'[1-9A-HJ-NP-Za-km-z]{32,44}', text)  # Updated regex for Solana addresses
    #logging.info(matches[3])
    amount_match = re.search(amount_pattern, text)

    if not matches: #or not amount_match:
       # logging.info(matches)
        #logging.info("looooooooooll")
        #return None
        pass
        

    # Return the third Solana address if it existslogging
    return  matches
    #logging.info(matches)

def extract_mc_mcp(text):
    """Extract the complete MC/MCP information including value, unit, and currency symbol."""
    mc_mcp_pattern = r'(MC|MCP):\s*(\$?\d+(?:\.\d+)?[KMB]?\$?(?:\s*[Mm][Ii][Ll][Ll][Ii][Oo][Nn])?)'
    match = re.search(mc_mcp_pattern, text, re.IGNORECASE)

    if match:
        mc_type = match.group(1)
        value_info = match.group(2)
        return f"{mc_type}:{value_info}"
    #return None

class Trade:
    def __init__(self, trader, amount, mc_mcp_info, pump_type):
        self.trader = trader
        self.amount = amount
        self.mc_mcp_info = mc_mcp_info
        self.pump_type = pump_type

async def extract_last_trader_messages(chat_link, limit):
    """Extract the last messages from the specified Telegram chat that meet the trader criteria"""
    trader_data = {}  # Dictionary to store trader information
    

    async for message in telethon_client.iter_messages(chat_link, limit=limit):
       
        
        # Check if the message contains 'buy' (case insensitive)
        if 'buy' in message.text.lower():
            trader_name = "Trader"+extract_trader_name(message.text)  # Extract trader name
            #logging.info(trader_name)
            solana_addresses = extract_solana_address_and_amount(message.text)  # Extract all Solana addresses
            #logging.info(solana_addresses)
            if solana_addresses:
                if chat_link == 'https://t.me/spark_green_bot':
                    third_address = solana_addresses[5]
                    #logging.info(third_address)
                elif chat_link == 'https://t.me/ray_green_bot':
                    third_address = solana_addresses[5]
                    #logging.info(third_address)
                    
                elif chat_link == 'https://t.me/Godeye_wallet_trackerBot':
                    third_address = solana_addresses[2]
                    #logging.info(third_address)                    
                    #logging.info(third_address)
                    #ogging.info(third_address)
                elif chat_link == 'https://t.me/Wallet_tracker_solana_spybot':
                    third_address = solana_addresses[6]
                    #logging.info(third_address)
                    #logging.info(third_address)
                      # Check if there are at least 3 addresses
                else:
                    third_address = solana_addresses[-1]
                    #logging.info(third_address)  # Get the third Solana address
                # Update the trader data dictionary
                if trader_name not in trader_data:
                    trader_data[trader_name] = {'addresses': {}, 'count': 0}  # Initialize new trader entry
                
                # Check if the address already exists for this trader
                if third_address in trader_data[trader_name]['addresses']:
                    trader_data[trader_name]['addresses'][third_address] += 1  # Increment count for this address
                else:
                    trader_data[trader_name]['addresses'][third_address] = 1  # Initialize count for new address
                
                # Update the total count of messages for the trader
                trader_data[trader_name]['count'] += 1
    
    #logging.info(trader_data)
    return trader_data
    
    
 

async def stop(update, context):
    global continue_scraping  # Ensure we're using the global variable
    if not await check_authorization(update):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"You are not eligible to use the bot. Your username: {update.effective_user.username}"
        )
        return

    if not continue_scraping:  # Check if the bot is already stopped
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Bot already stopped."
        )
        return

    continue_scraping = False  # Stop the scraping process now
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Stopping continuous scraping. The current round will complete before stopping."
    )

async def send_trader_messages(trader_data, chat_id, context):
    """Send messages for each trader and their purchased tokens."""
    messages_to_send = []
    for trader_name, data in trader_data.items():
        for token, count in data['addresses'].items():
            if count == 2:  # Check if the trader bought the token more than once
                message = f"{trader_name} bought `{token}` {count} times"
                messages_to_send.append(message)
    return messages_to_send

async def continuous_scraping(update, context):
    """Continuously scrape messages in rounds"""
    global continue_scraping
    continue_scraping = True
    chat_id = update.effective_chat.id

    chat_links_with_limits = {
        'https://t.me/spark_green_bot': 30,
        'https://t.me/ray_green_bot': 60,
        #'https://t.me/handi_cat_bot': 300,
        'https://t.me/Wallet_tracker_solana_spybot': 30,
        'https://t.me/Godeye_wallet_trackerBot': 60,
        #'https://t.me/GMGN_alert_bot': 150,
        #'https://t.me/Solbix_bot': 30,
        'https://t.me/defined_bot': 90
    }
    #logging.info("seen")
    previous_messages = []
    while continue_scraping:
        #logging.info("still scrapping")
        new_messages_found = False
        
        
        for chat_link, limit in chat_links_with_limits.items():
            await asyncio.sleep(0.8)
            messages = await extract_last_trader_messages(chat_link, limit)

            listOfMultipleBuys = await send_trader_messages(messages, chat_id, context)

            current_messages = []
            has_change = False
            for message in listOfMultipleBuys:
                #await context.bot.send_message(chat_id=chat_id, text=message)
                current_messages.append(message)
                #await asyncio.sleep(2.0)
                #logging.info(current_messages)
            #previous_messages = current_messages.copy()  # Update previous_messages to the current round's message
            
            
            sent_count = 0  # Counter to track the number of messages sent
            for message in current_messages[:200]:
                
                if message not in previous_messages[:200]:
                    has_change = True
                    #logging.info(message)
                    previous_messages.append(message)
                    
                    

                    if sent_count < 2:  # Check if less than 2 messages have been sent
                        await context.bot.send_message(
                            chat_id=target_group_id,
                            text=message,
                            parse_mode='Markdown'
                        )
                        
                        sent_count += 1  # Increment the counter
            if has_change is False:
               logging.info("no new messages")
               await asyncio.sleep(2.2)
               #await asyncio.sleep()
        
        # Wait 10 seconds before starting the next round
        await asyncio.sleep(2)

async def start(update, context):
    """Start the continuous message extraction process"""
    if (await check_authorization(update)):
        if update.effective_chat.id == -1002272071296:  # Check if the command is from the target gr
            global target_group_id
            target_group_id = -1002447422257
            if update.message.text.startswith(f"@{BOT_TOKEN.split(':')[0]}"):
                last_processed_messages.clear()
                await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Starting continuous message scraping. Use /stop to end the process."
            )
                await continuous_scraping(update, context)
            else:
                await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Please use the command in the format '@YourBotUsername start'"
            )
            # Start the continuous scraping
            await continuous_scraping(update, context)
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="This command can only be used in the authorized target group."
            )
    
   
    
    

# Initialize Flask app
flask_app = Flask(__name__)

@flask_app.route('/webhook', methods=['POST'])
def webhook():
    """Receive updates from Telegram and process them."""
    update = request.get_json()
    # Here you can process the update as needed
    logging.info(f"Received update: {update}")
    return "OK", 200

@flask_app.route('/', methods=['GET'])
def home():
    """Check if the bot is running."""
    return "The bot is running!", 200  # Simple message indicating the bot is active

def run_flask():
    """Run the Flask app."""
    flask_app.run(host='0.0.0.0', port=5000)  # Run Flask on port 5000

async def main():
    """Start the bot with webhook"""
    await initialize_telethon()  # Start the Telethon client

    # Initialize Application instance for webhook mode
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers for both start and stop commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))

    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    # Set the webhook for the Telegram bot
    try:
        await asyncio.sleep(1.0)
        await application.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")  # Update webhook URL
        await asyncio.sleep(1.0)
        await application.run_webhook(
            listen="0.0.0.0",  # Listen on all available interfaces
            port=10000,         # Port to listen on
            url_path="",       # Empty path to handle root requests
            webhook_url=WEBHOOK_URL,
            drop_pending_updates=True
        )
        return application

    except Exception as e:
        logging.error(f"Error in webhook setup: {e}")
        raise

def run_bot():
    """Runner function to handle the event loop"""
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

    try:
        loop = asyncio.get_event_loop()
        application = loop.run_until_complete(main())
        
        # Updated webhook configuration for Render
        application.run_webhook(
            listen="0.0.0.0",  # Listen on all available network interfaces
            port=PORT,         # Use the PORT from environment variable
            url_path=BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",  # Use Render's external URL
            drop_pending_updates=True
        )
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        raise

if __name__ == "__main__":
    run_bot()
