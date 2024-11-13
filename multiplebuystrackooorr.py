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
from keep_alive import keep_alive

#{os.getenv('RENDER_EXTERNAL_URL', '')}
#PORT = int(os.getenv("PORT", 8443))

keep_alive()

nest_asyncio.apply()

# Telegram bot configuration
dotenv_path = find_dotenv()
load_dotenv(dotenv_path)


PORT = int(os.getenv("PORT", 10000))

# Telethon client configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")



# Create Telethon client
telethon_client = TelegramClient('test', API_ID, API_HASH)

# Authorized users and groups (store without @ symbol)
AUTHORIZED_USERS = {'orehub1378', 'Kemoo1975', 'jeremi1234', 'Busiiiiii'}
AUTHORIZED_GROUPS = {'TheTrackoorzz'}

# Add a dictionary to store the last processed message IDs for each chat
last_processed_messages = defaultdict(set)
# Flag to control continuous scraping
continue_scraping = True

async def check_authorization(update):
    """Check if the user/group is authorized to use the bot"""
    chat_id = update.effective_chat.id
    user_username = update.effective_user.username
    chat_username = update.effective_chat.username
    
    if update.effective_chat.type == 'private':
        return user_username and user_username.lower() in {user.lower() for user in AUTHORIZED_USERS}
    
    return chat_username and chat_username.lower() in {group.lower() for group in AUTHORIZED_GROUPS}

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

def extract_solana_address_and_amount(text, first_only=False):
    """Extract the Solana address and the float/integer amount just before 'SOL'."""
    solana_pattern = r'[1-9A-HJ-NP-Za-km-z]{32,44}'
    amount_pattern = r'(\b\d+(\.\d+)?(?=\s+SOL\b))'

    matches = re.findall(solana_pattern, text)
    amount_match = re.search(amount_pattern, text)

    if not matches or not amount_match:
        return None

    solana_address = matches[0] if first_only else matches[-1]
    amount = amount_match.group()

    return amount, solana_address

def extract_mc_mcp(text):
    """Extract the complete MC/MCP information including value, unit, and currency symbol."""
    mc_mcp_pattern = r'(MC|MCP):\s*(\$?\d+(?:\.\d+)?[KMB]?\$?(?:\s*[Mm][Ii][Ll][Ll][Ii][Oo][Nn])?)'
    match = re.search(mc_mcp_pattern, text, re.IGNORECASE)

    if match:
        mc_type = match.group(1)
        value_info = match.group(2)
        return f"{mc_type}:{value_info}"
    return None

class Trade:
    def __init__(self, trader, amount, mc_mcp_info, pump_type):
        self.trader = trader
        self.amount = amount
        self.mc_mcp_info = mc_mcp_info
        self.pump_type = pump_type

async def extract_last_trader_messages(chat_link, limit):
    """Extract the last messages from the specified Telegram chat that meet the trader criteria"""
    async with telethon_client:
        # Use defaultdict to track trades by address
        address_trades = defaultdict(list)
        
        async for message in telethon_client.iter_messages(chat_link, limit=limit):
            if message.text and is_trader_message(message.text):
                trader_suffix = extract_trader_name(message.text)
                pump_type = extract_pump_type(message.text)
                
                # Skip messages with unknown pump type
                if pump_type == 'Unknown':
                    continue
                
                if chat_link == 'https://t.me/Godeye_wallet_trackerBot':
                    extracted_data = extract_solana_address_and_amount(message.text, first_only=True)
                else:
                    extracted_data = extract_solana_address_and_amount(message.text)

                if extracted_data:
                    amount, sol_address = extracted_data
                    mc_mcp_info = extract_mc_mcp(message.text) or ""
                    
                    # Add trade to the address's list with trader information
                    address_trades[sol_address].append(
                        Trade(trader_suffix, amount, mc_mcp_info, pump_type)
                    )

        # Format messages based on trades
        formatted_messages = []
        for address, trades in address_trades.items():
            # Group trades by trader
            traders_dict = defaultdict(list)
            for trade in trades:
                traders_dict[trade.trader].append(trade)
            
            # Process addresses based on number of unique traders
            unique_traders = len(traders_dict)
            
            if unique_traders > 1:
                # Multiple traders format
                header = f"{unique_traders} traders bought {address}"
                trade_details = []
                for i, (trader, trader_trades) in enumerate(traders_dict.items(), 1):
                    for trade in trader_trades:
                        mc_info = f" at {trade.mc_mcp_info}" if trade.mc_mcp_info else ""
                        trade_details.append(f"Trader {i}, {trade.amount} SOL{mc_info} via {trade.pump_type}")
                formatted_messages.append(header + "\n" + "\n".join(trade_details))
            
            elif unique_traders == 1:
                # Single trader with multiple buys format
                trader, trader_trades = next(iter(traders_dict.items()))
                if len(trader_trades) > 1:
                    header = f"TRADER{trader} bought {address} {len(trader_trades)} times"
                    buys = []
                    for i, trade in enumerate(trader_trades, 1):
                        mc_info = f" at {trade.mc_mcp_info}" if trade.mc_mcp_info else ""
                        buys.append(f"Buy {i}, {trade.amount} SOL{mc_info} via {trade.pump_type}")
                    formatted_messages.append(header + "\n" + "\n".join(buys))

        return formatted_messages

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

async def continuous_scraping(update, context):
    """Continuously scrape messages in rounds"""
    global continue_scraping
    continue_scraping = True
    chat_id = update.effective_chat.id

    chat_links_with_limits = {
        'https://t.me/ray_silver_bot': 150,
        'https://t.me/handi_cat_bot': 300,
        'https://t.me/Wallet_tracker_solana_spybot': 75,
        'https://t.me/Godeye_wallet_trackerBot': 150,
        'https://t.me/GMGN_alert_bot': 150,
        'https://t.me/Solbix_bot': 30
    }

    while continue_scraping:
        new_messages_found = False
        
        for chat_link, limit in chat_links_with_limits.items():
            messages = await extract_last_trader_messages(chat_link, limit)
            
            # Filter out previously processed messages
            new_messages = []
            for message in messages:
                # Create a hash of the message content to use as an identifier
                message_hash = hash(message)
                if message_hash not in last_processed_messages[chat_link]:
                    new_messages.append(message)
                    last_processed_messages[chat_link].add(message_hash)
                    new_messages_found = True
            
            # Send only new messages
            for message in new_messages:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=message
                )
                await asyncio.sleep(0.1)  # Small delay between messages
        
        if not new_messages_found:
            await context.bot.send_message(
                chat_id=chat_id,
                text="No new messages found in this round."
            )
        
        # Wait 10 seconds before starting the next round
        await asyncio.sleep(10)

async def start(update, context):
    """Start the continuous message extraction process"""
    if (await check_authorization(update)):
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
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Starting continuous message scraping. Use /stop to end the process."
    )
    
    # Start the continuous scraping
    await continuous_scraping(update, context)

async def main():
    """Start the bot with webhook"""
    application = Application.builder().token(BOT_TOKEN).http_version("1.1").build()
    application.bot_data["application"] = application

    # Add handlers for both start and stop commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))

    # Get the webhook URL from environment variable or use a default for local testing
    WEBHOOK_URL = "ceb0-102-135-211-94.ngrok-free.app"
    
    try:
        await application.bot.set_webhook(
            url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
            allowed_updates=["message", "callback_query"]
        )
        await application.initialize()
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
            webhook_url=f"ceb0-102-135-211-94.ngrok-free.app/{BOT_TOKEN}",
            drop_pending_updates=True
        )

    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        raise

if __name__ == "__main__":
    run_bot()
