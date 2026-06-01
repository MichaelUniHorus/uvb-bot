import asyncio
import csv
import os
import json
from datetime import datetime, timedelta
from telethon import TelegramClient, events
from telethon.network.connection import ConnectionTcpMTProxyAbridged
from config import API_ID, API_HASH, CHANNEL_NAME, BOT_TOKEN, USE_PROXY, PROXY_AUTO_UPDATE, MANUAL_PROXY
from parser import parse_nzti_message, has_nzti_tag
from proxy_manager import proxy_manager, init_proxy_manager

# Initialize proxy manager with manual proxy if provided
init_proxy_manager(MANUAL_PROXY)

CSV_FILE = "nzti_data.csv"
SUBSCRIBERS_FILE = "subscribers.json"
MAX_RETRIES = 3
RETRY_DELAY = 5

def load_subscribers():
    if os.path.exists(SUBSCRIBERS_FILE):
        with open(SUBSCRIBERS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_subscribers(subs):
    with open(SUBSCRIBERS_FILE, 'w') as f:
        json.dump(subs, f)

def get_yesterday_date():
    yesterday = datetime.now() - timedelta(days=1)
    return yesterday.strftime("%d.%m.%y")

async def get_client_with_proxy(use_bot=False):
    """Create Telethon client with proxy support"""
    proxy = None
    connection = None
    
    if USE_PROXY:
        if PROXY_AUTO_UPDATE:
            await proxy_manager.load_proxies()
        
        proxy = proxy_manager.get_current_proxy()
        if proxy:
            host, port, secret = proxy
            print(f"Using proxy: {host}:{port}")
            proxy = (host, port, secret)
            connection = ConnectionTcpMTProxyRandomized
    
    if use_bot:
        return TelegramClient('bot_session', int(API_ID), API_HASH, proxy=proxy, connection=connection)
    else:
        return TelegramClient('session', int(API_ID), API_HASH, proxy=proxy, connection=connection)

async def fetch_yesterday_messages():
    yesterday_str = get_yesterday_date()
    print(f"Looking for date: {yesterday_str}")
    
    for attempt in range(MAX_RETRIES):
        try:
            client = await get_client_with_proxy(use_bot=False)
            
            async with client:
                await client.start(phone=lambda: input("Phone: "), 
                                  code_callback=lambda: input("Code: "))
                
                channel_username = CHANNEL_NAME.replace("t.me/", "")
                entity = await client.get_entity(f"@{channel_username}")
                
                messages = []
                async for message in client.iter_messages(entity, limit=100):
                    if message.text and has_nzti_tag(message.text):
                        parsed = parse_nzti_message(message.text)
                        if parsed:
                            print(f"Found message: date={parsed.date}, time={parsed.time}")
                        if parsed and parsed.date == yesterday_str:
                            messages.append(parsed)
                            print(f"MATCH: {parsed.date} {parsed.time} - НЖТИ {parsed.nzti} {parsed.name}")
                
                print(f"Total found: {len(messages)}")
                return messages
        except Exception as e:
            print(f"Attempt {attempt + 1}/{MAX_RETRIES} failed: {e}")
            if USE_PROXY:
                await proxy_manager.next_proxy()
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY)
    
    raise Exception("Failed to fetch messages after all retries")

def format_report(messages):
    if not messages:
        return "Нет данных за вчера"
    
    lines = [f"📊 Сводка за {get_yesterday_date()}\n"]
    for m in messages:
        lines.append(f"• {m.time} | {m.nzti} | {m.name} | {m.number1} {m.number2}")
    
    return "\n".join(lines)

def save_to_csv(data):
    with open(CSV_FILE, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['Дата', 'Время', 'НЖТИ', 'Название', 'Число1', 'Число2'])
        for item in data:
            writer.writerow([item.date, item.time, item.nzti, item.name, item.number1, item.number2])

async def send_to_subscribers(report):
    subs = load_subscribers()
    if not subs:
        print("No subscribers")
        return
    
    for attempt in range(MAX_RETRIES):
        try:
            client = await get_client_with_proxy(use_bot=True)
            await client.start(bot_token=BOT_TOKEN)
            
            for chat_id in subs:
                try:
                    await client.send_message(int(chat_id), report)
                    print(f"Sent to {chat_id}")
                except Exception as e:
                    print(f"Error sending to {chat_id}: {e}")
            
            await client.disconnect()
            return
        except Exception as e:
            print(f"Attempt {attempt + 1}/{MAX_RETRIES} failed: {e}")
            if USE_PROXY:
                await proxy_manager.next_proxy()
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY)
    
    print("Failed to send report after all retries")

async def run_bot():
    print("Initializing bot...")
    
    if USE_PROXY and PROXY_AUTO_UPDATE:
        await proxy_manager.load_proxies()
        working_proxy = await proxy_manager.find_working_proxy()
        if not working_proxy:
            print("Warning: No working proxy found, trying without proxy...")
    
    for attempt in range(MAX_RETRIES):
        try:
            client = await get_client_with_proxy(use_bot=True)
            
            @client.on(events.NewMessage(pattern='/start'))
            async def start_handler(event):
                chat_id = str(event.chat_id)
                subs = load_subscribers()
                if chat_id not in subs:
                    subs.append(chat_id)
                    save_subscribers(subs)
                await event.reply("Подписка оформлена!")
            
            print("Bot running... Press Ctrl+C to stop")
            await client.start(bot_token=BOT_TOKEN)
            await client.run_until_disconnected()
            return
        except Exception as e:
            print(f"Attempt {attempt + 1}/{MAX_RETRIES} failed: {e}")
            if USE_PROXY:
                await proxy_manager.next_proxy()
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY)
    
    raise Exception("Failed to start bot after all retries")

def add_subscriber(chat_id):
    subs = load_subscribers()
    chat_id = str(chat_id)
    if chat_id not in subs:
        subs.append(chat_id)
        save_subscribers(subs)
        print(f"Added subscriber: {chat_id}")
    else:
        print(f"Already subscribed: {chat_id}")

def list_subscribers():
    subs = load_subscribers()
    print(f"Subscribers: {len(subs)}")
    for s in subs:
        print(f"  - {s}")

async def send_report():
    print(f"Fetching messages for {get_yesterday_date()}...")
    
    if USE_PROXY and PROXY_AUTO_UPDATE:
        await proxy_manager.load_proxies()
    
    messages = await fetch_yesterday_messages()
    
    if messages:
        save_to_csv(messages)
        report = format_report(messages)
        await send_to_subscribers(report)
        print(f"\nSaved {len(messages)} records")
    else:
        await send_to_subscribers(f"Нет данных за {get_yesterday_date()}")

def main():
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "bot":
            asyncio.run(run_bot())
        elif sys.argv[1] == "add" and len(sys.argv) > 2:
            add_subscriber(sys.argv[2])
        elif sys.argv[1] == "list":
            list_subscribers()
        else:
            print("Usage: python crawler.py [bot|add <chat_id>|list]")
    else:
        asyncio.run(send_report())

if __name__ == "__main__":
    main()
