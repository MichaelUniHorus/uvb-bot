import asyncio
import aiohttp
import time
from typing import List, Tuple, Optional
from datetime import datetime, timedelta
import os

PROXY_LIST_URL = "https://raw.githubusercontent.com/SoliSpirit/mtproto/master/all_proxies.txt"
PROXY_CACHE_FILE = "proxy_cache.txt"
PROXY_UPDATE_INTERVAL = 12 * 60 * 60  # 12 hours in seconds

# Fallback built-in proxies (in case GitHub is blocked)
BUILTIN_PROXIES = [
    # Add some known working MTProxy proxies here
    # Format: host:port:secret
    # These are examples - replace with actual working proxies
]

class ProxyManager:
    def __init__(self, manual_proxy: str = ""):
        self.proxies: List[Tuple[str, int, str]] = []  # (host, port, secret)
        self.current_index = 0
        self.last_update = 0
        self.lock = asyncio.Lock()
        
        # Add manual proxy if provided
        if manual_proxy:
            self._parse_proxies(manual_proxy)
            print(f"Added manual proxy: {len(self.proxies)}")
        
    async def load_proxies(self) -> bool:
        """Load proxies from cache or download fresh ones"""
        cache_path = PROXY_CACHE_FILE
        
        # First try to load from manual file if exists
        manual_file = "manual_proxies.txt"
        if os.path.exists(manual_file):
            with open(manual_file, 'r', encoding='utf-8') as f:
                self._parse_proxies(f.read())
            print(f"Loaded {len(self.proxies)} proxies from manual file")
            if len(self.proxies) > 0:
                return True
        
        # Check if cache exists and is fresh
        if os.path.exists(cache_path):
            cache_time = os.path.getmtime(cache_path)
            if time.time() - cache_time < PROXY_UPDATE_INTERVAL:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    self._parse_proxies(f.read())
                print(f"Loaded {len(self.proxies)} proxies from cache")
                return len(self.proxies) > 0
        
        # Download fresh proxies
        result = await self.download_proxies()
        
        # Fallback to built-in proxies if download failed
        if not result and BUILTIN_PROXIES:
            self._parse_proxies('\n'.join(BUILTIN_PROXIES))
            print(f"Loaded {len(self.proxies)} built-in proxies")
            return len(self.proxies) > 0
        
        return result
    
    async def download_proxies(self) -> bool:
        """Download fresh proxies from GitHub"""
        try:
            print(f"Downloading proxies from {PROXY_LIST_URL}...")
            async with aiohttp.ClientSession() as session:
                async with session.get(PROXY_LIST_URL, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    print(f"Response status: {response.status}")
                    if response.status == 200:
                        content = await response.text()
                        print(f"Downloaded {len(content)} bytes")
                        self._parse_proxies(content)
                        
                        # Save to cache
                        with open(PROXY_CACHE_FILE, 'w', encoding='utf-8') as f:
                            f.write(content)
                        
                        print(f"Downloaded {len(self.proxies)} fresh proxies")
                        return len(self.proxies) > 0
                    else:
                        print(f"Failed to download: HTTP {response.status}")
        except Exception as e:
            print(f"Error downloading proxies: {e}")
        
        # Fallback to cache if download failed
        if os.path.exists(PROXY_CACHE_FILE):
            with open(PROXY_CACHE_FILE, 'r', encoding='utf-8') as f:
                self._parse_proxies(f.read())
            print(f"Using cached proxies: {len(self.proxies)}")
            return len(self.proxies) > 0
        
        return False
    
    def _parse_proxies(self, content: str):
        """Parse proxy list from text content"""
        self.proxies = []
        for line in content.strip().split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Format: https://t.me/proxy?server=...&port=...&secret=...
            if line.startswith('https://t.me/proxy?'):
                try:
                    from urllib.parse import parse_qs, urlparse
                    parsed = urlparse(line)
                    params = parse_qs(parsed.query)
                    
                    if 'server' in params and 'port' in params and 'secret' in params:
                        host = params['server'][0]
                        port = int(params['port'][0])
                        secret = params['secret'][0]
                        self.proxies.append((host, port, secret))
                except Exception as e:
                    print(f"Error parsing proxy line: {e}")
                    continue
            
            # Fallback: Format: host:port:secret
            else:
                parts = line.split(':')
                if len(parts) >= 3:
                    try:
                        host = parts[0]
                        port = int(parts[1])
                        secret = ':'.join(parts[2:])  # Secret may contain colons
                        self.proxies.append((host, port, secret))
                    except ValueError:
                        continue
    
    def get_current_proxy(self) -> Optional[Tuple[str, int, str]]:
        """Get current proxy"""
        if not self.proxies:
            return None
        return self.proxies[self.current_index]
    
    async def next_proxy(self) -> Optional[Tuple[str, int, str]]:
        """Switch to next proxy"""
        async with self.lock:
            if not self.proxies:
                return None
            
            self.current_index = (self.current_index + 1) % len(self.proxies)
            proxy = self.proxies[self.current_index]
            print(f"Switched to proxy {self.current_index + 1}/{len(self.proxies)}: {proxy[0]}:{proxy[1]}")
            return proxy
    
    async def test_proxy(self, host: str, port: int, secret: str) -> bool:
        """Test if proxy is working by trying to connect"""
        try:
            from telethon import TelegramClient
            from telethon.network.connection import ConnectionTcpMTProxyAbridged
            from config import API_ID, API_HASH
            
            # Use a temporary client to test connection
            test_client = TelegramClient(
                None,
                int(API_ID),
                API_HASH,
                proxy=(host, port, secret),
                connection=ConnectionTcpMTProxyAbridged
            )
            
            # Try to connect with timeout
            await asyncio.wait_for(test_client.connect(), timeout=10)
            await test_client.disconnect()
            return True
        except Exception as e:
            print(f"Proxy test failed for {host}:{port}: {e}")
            return False
    
    async def find_working_proxy(self) -> Optional[Tuple[str, int, str]]:
        """Find a working proxy by testing them"""
        if not self.proxies:
            await self.load_proxies()
        
        if not self.proxies:
            return None
        
        print(f"Testing {len(self.proxies)} proxies...")
        
        for i in range(len(self.proxies)):
            proxy = self.proxies[self.current_index]
            host, port, secret = proxy
            
            if await self.test_proxy(host, port, secret):
                print(f"Found working proxy: {host}:{port}")
                return proxy
            
            await self.next_proxy()
        
        print("No working proxy found")
        return None

# Global proxy manager instance
proxy_manager = ProxyManager()
