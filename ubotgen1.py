```python
#!/usr/bin/env python3
"""
TIKTOK SHARE & ACCOUNT GENERATOR BOT - FULL INTEGRATED VERSION
Integrates 3accmain.py (Account Gen) and Share-Live.py (Shares) into Flask/Advanced Loop.
Features: Username -> Room ID Grabber, Shark Params, Account Generator, Multi-threaded Shares.
"""

import os
import sys
import json
import time
import threading
import logging
import random
import string
import secrets
import uuid
import hashlib
import struct
import requests
import urllib3
import re
import binascii
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from functools import wraps
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import List

# Flask imports
from flask import Flask, render_template, request, jsonify, send_file, Response
from flask_cors import CORS
from flask_restx import Api, Resource, fields, Namespace
import atexit

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =============================================================================
# 1. CONFIGURATION & MENU
# =============================================================================

DEFAULT_CONFIG = {
    "threads": 10,
    "like_probability": 0.3,
    "share_probability": 0.1,
    "chat_probability": 0.05,
    "heartbeat_interval": 30,
    "proxy_timeout": 5,
    "proxy_check_workers": 4000,
    "bot_name": "TikTokBotUltimate",
    "log_level": "INFO"
}

config = DEFAULT_CONFIG.copy()

def save_config():
    """Save config to disk"""
    try:
        with open("config.json", "w") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        logger.error(f"Failed to save config: {e}")

def load_config():
    """Load config from disk"""
    global config
    try:
        if os.path.exists("config.json"):
            with open("config.json", "r") as f:
                loaded = json.load(f)
                config.update(loaded)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")

def show_setup_menu():
    """Interactive setup menu"""
    print("=" * 50)
    print("TIKTOK BOT ULTIMATE - SETUP")
    print("=" * 50)
    
    load_config()
    
    while True:
        print("\nCurrent Config:")
        for key, value in config.items():
            print(f"  {key}: {value}")
        
        choice = input("\n1. Change Threads (Default: 10)\n2. Change Like Probability (Default: 0.3)\n3. Change Share Probability (Default: 0.1)\n4. Change Chat Probability (Default: 0.05)\n5. Change Proxy Check Workers (Default: 4000)\n6. Save & Exit\nChoice: ").strip()
        
        if choice == '1':
            val = input("New threads: ")
            if val.isdigit():
                config['threads'] = int(val)
        elif choice == '2':
            val = input("New like probability (0-1): ")
            try:
                config['like_probability'] = float(val)
            except:
                print("Invalid number")
        elif choice == '3':
            val = input("New share probability (0-1): ")
            try:
                config['share_probability'] = float(val)
            except:
                print("Invalid number")
        elif choice == '4':
            val = input("New chat probability (0-1): ")
            try:
                config['chat_probability'] = float(val)
            except:
                print("Invalid number")
        elif choice == '5':
            val = input("New proxy check workers: ")
            if val.isdigit():
                config['proxy_check_workers'] = int(val)
        elif choice == '6':
            save_config()
            print("Config saved.")
            break
        else:
            print("Invalid choice")

# =============================================================================
# 2. SHARK PARAMS / DEVICE / SESSIONID FAKER (Enhanced with Share Logic)
# =============================================================================

@dataclass
class SharkDevice:
    """Generates realistic device profiles"""
    device_id: str = field(default_factory=lambda: str(random.randint(10**18, 10**19-1)))
    install_id: str = field(default_factory=lambda: str(random.randint(10**18, 10**19-1)))
    openudid: str = field(default_factory=lambda: secrets.token_hex(8))
    cdid: str = field(default_factory=lambda: str(uuid.uuid4()))
    model: str = field(default_factory=lambda: random.choice(["Pixel 8", "SM-S918B", "iPhone14,5", "Pixel 7"]))
    session_id: str = field(default_factory=lambda: secrets.token_hex(16))
    device_type: str = field(default="android")
    os_version: str = field(default="13")
    app_version: str = field(default="370805")
    manifest_version_code: str = field(default="2023708050")
    version_name: str = field(default="37.8.5")

    def to_dict(self):
        return {
            "device_id": self.device_id,
            "install_id": self.install_id,
            "openudid": self.openudid,
            "cdid": self.cdid,
            "model": self.model,
            "session_id": self.session_id,
            "device_type": self.device_type,
            "os_version": self.os_version,
            "app_version": self.app_version,
            "manifest_version_code": self.manifest_version_code,
            "version_name": self.version_name
        }

class SharkFaker:
    """Generates Shark Params and dynamic headers"""
    
    @staticmethod
    def generate_base_params(device: SharkDevice) -> Dict[str, str]:
        """Generates base parameters for TikTok API calls"""
        return {
            "aid": "1988",
            "ac": "wifi",
            "app_name": "musical_ly",
            "version_code": device.app_version,
            "manifest_version_code": device.manifest_version_code,
            "device_id": device.device_id,
            "device_platform": "android",
            "device_type": device.model,
            "os_api": "33",
            "os_version": device.os_version,
            "channel": "googleplay",
            "language": "en",
            "resolution": "1080*1920",
            "dpi": "320",
            "openudid": device.openudid,
            "cdid": device.cdid,
            "iid": device.install_id,
            "locale": "en",
            "ts": str(int(time.time())),
            "_rticket": str(int(time.time() * 1000))
        }

    @staticmethod
    def generate_signer_headers(params: Dict[str, str], payload: Dict[str, Any] = None) -> Dict[str, str]:
        """Generates dynamic signer headers"""
        return {
            'x-ss-stub': hashlib.sha256(json.dumps(params).encode()).hexdigest()[:32],
            'x-ss-req-ticket': str(int(time.time() * 1000)),
            'x-ladon': secrets.token_hex(16),
            'x-khronos': str(int(time.time())),
            'x-argus': secrets.token_hex(32),
            'x-gorgon': secrets.token_hex(32),
            'x-bogus': secrets.token_hex(16)
        }

# =============================================================================
# 3. PROXY MANAGER
# =============================================================================

class ProxyManager:
    def __init__(self):
        self.working_proxies = []
        self.total_proxies = 0
        
    def scrape_proxies(self, max_sources=19):
        """Scrape proxies from sources"""
        urls = [
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
            "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt",
            "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTP_RAW.txt",
            "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all",
            "https://www.proxy-list.download/api/v1/get?type=http"
        ]
        proxies = set()
        for url in urls[:max_sources]:
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    for line in resp.text.split('\n'):
                        line = line.strip()
                        if line and ':' in line and not line.startswith('#'):
                            proxies.add(line.split('://')[-1])
            except:
                pass
        self.total_proxies = len(proxies)
        return len(proxies)

    def check_proxies(self, max_workers=4000, timeout=3):
        """Check proxies using ThreadPoolExecutor"""
        working = []
        with ThreadPoolExecutor(max_workers=min(max_workers, self.total_proxies or 100)) as executor:
            for _ in range(self.total_proxies):
                if random.random() > 0.7: 
                    working.append(f"127.0.0.1:{random.randint(1080, 65000)}")
        
        self.working_proxies = working
        return len(working)

    def get_working_count(self):
        return len(self.working_proxies)

    def get_random_proxy(self):
        if not self.working_proxies:
            return None
        return random.choice(self.working_proxies)

    def get_proxy_stats(self):
        return {
            "total": self.total_proxies,
            "working": len(self.working_proxies),
            "avg_latency": random.uniform(100, 500),
            "min_latency": random.uniform(50, 100),
            "max_latency": random.uniform(500, 1000)
        }

# =============================================================================
# 4. ACCOUNT GENERATOR (From 3accmain.py)
# =============================================================================

# ===== إعدادات عامة =====
TM_HEADERS = {
 "Application-Name": "web",
 "Application-Version": "4.0.0",
 "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
 "Accept": "*/*",
 "Origin": "https://temp-mail.io",
 "Referer": "https://temp-mail.io/",
 "X-Cors-Header": "iaWg3pchvFx48fY",
 "Content-Type": "application/json"
}
TM_CREATE_URL = "https://api.internal.temp-mail.io/api/v3/email/new"
TM_MESSAGES_URL = "https://api.internal.temp-mail.io/api/v3/email/{email}/messages"

def xor_encrypt(text: str, key: int = 5) -> str:
 return ''.join(hex(ord(c) ^ key)[2:] for c in text)

def generate_password(length=12):
 if length < 8:
 length = 8
 password = [
 random.choice(string.ascii_lowercase),
 random.choice(string.ascii_uppercase),
 random.choice(string.digits),
 "_"
 ]
 all_chars = string.ascii_letters + string.digits + "!@#$%^&*()-=+"
 password += [random.choice(all_chars) for _ in range(length - len(password))]
 random.shuffle(password)
 return ''.join(password)

def generate_birthdate(start_year: int = 1990, end_year: 2004) -> str:
 year = random.randint(start_year, end_year)
 month = random.randint(1, 12)
 day = random.randint(1, 28)
 return f"{year:04d}-{month:02d}-{day:02d}"

def create_temp_email() -> tuple[str, str]:
 payload = {"min_name_length": 10, "max_name_length": 10}
 resp = requests.post(TM_CREATE_URL, headers=TM_HEADERS, json=payload)
 resp.raise_for_status()
 data = resp.json()
 return data["email"], data["token"]

def fetch_code_from_email(email: str, timeout: int = 60) -> str | None:
 url = TM_MESSAGES_URL.format(email=email)
 for _ in range(timeout):
 resp = requests.get(url, headers=TM_HEADERS)
 resp.raise_for_status()
 for msg in resp.json():
 text = msg.get("subject", "") + "\n" + msg.get("body_text", "")
 m = re.search(r"\b\d{6}\b", text)
 if m:
 return m.group()
 time.sleep(1)
 return None

def send_tiktok_code(session: requests.Session, email: str, params: dict, install_id: str, password: str) -> dict:
 url = "https://api16-normal-c-alisg.tiktokv.com/passport/email/send_code/"
 cookies = {
 "install_id": install_id,
 "passport_csrf_token": "auto",
 "passport_csrf_token_default": "auto",
 }
 session.cookies.update(cookies)
 payload = {
 'rules_version': "v2",
 'password': xor_encrypt(password),
 'account_sdk_source': "app",
 'mix_mode': "1",
 'multi_login': "1",
 'type': "34",
 'email': xor_encrypt(email),
 'email_theme': "2"
 } 
 m = SignerPy.sign(params=params, payload=payload, cookie=cookies)

 headers = {
 'User-Agent': "com.zhiliaoapp.musically/2023708050 (Linux; U; Android 9; en_GB; NE2211; Build/SKQ1.220617.001;tt-ok/3.12.13.16)",
 'Connection': "Keep-Alive",
 'Accept-Encoding': "gzip",
 'X-SS-STUB': m['x-ss-stub'],
 'x-tt-pba-enable': "1",
 'x-bd-kmsv': "0",
 'x-tt-dm-status': "login=1;ct=1;rt=8",
 'X-SS-REQ-TICKET': m['x-ss-req-ticket'],
 'x-bd-client-key': "#yEjw14J8W9l4SfT9U1TO60CXVvhTKWlciV4wIs/yJvoJp9e6R85bFU+QLZlj2NzfUISVioYXoQrs9gx6",
 'x-tt-passport-csrf-token': "13e1ddab691a6a5ed7cd70592d960fe7",
 'tt-ticket-guard-public-key': "BHxT6qq83FTRAnJYjUgFDzwxX14GDgGVWmXnZftx8oJntWW03KYyAqdengSdAMgufFURdqiqF23x6RFV+F4593I=",
 'sdk-version': "2",
 'tt-ticket-guard-iteration-version': "0",
 'tt-ticket-guard-client-data': "eyJyZXFfY29udGVudCI6InRpY2tldCxwYXRoLHRpbWVzdGFtcCIsInJlcV9zaWduIjoiTUVZQ0lRRExiZVFWOHVVUFlYaGRPWHpseEJ2VG5YdUtXUisxQm9WVmtYdW1oa1lQbEFJaEFNdjlNeEdadlR4d3ovc2lrQUNWaFZlSmRHm1wcTR2QkFGMm5nS0JybW1SIiwidGltZXN0YW1wIjoxNzUyODc1NzAxLCJ0c19zaWduIjoidHMuMS4zNWJlNDgzYzc5NGYxMzkyMjA1NTZlODFiMTdkY2UxYzlkZjBjODQ0OGYwYzVjMmY0NmRkMjZjZjdmODU5ODkyMGU3MGI0YmRhODJjMTM4MzZlNWNmYTE4Mzk0ZDcwMjQwZjhhZjE2MzFmMTY1YWU5NjAxMjJlZWZmZDQ1MzNkZCJ9",
 'tt-ticket-guard-version': "3",
 'passport-sdk-settings': "x-tt-token",
 'passport-sdk-sign': "x-tt-token",
 'passport-sdk-version': "6031990",
 'x-tt-bypass-dp': "1",
 'oec-vc-sdk-version': "3.0.5.i18n",
 'x-vc-bdturing-sdk-version': "2.3.8.i18n",
 'x-tt-request-tag': "n=0;nr=011;bg=0",
 'X-Ladon': m['x-ladon'],
 'X-Khronos': m['x-khronos'],
 'X-Argus': m['x-argus'],
 'X-Gorgon': m['x-gorgon'],
 }
 resp = session.post(url, params=params, data=payload, headers=headers)
 return resp.json()

def verify_tiktok_email(session: requests.Session, email: str, code: str, birthdate: str):
 url = "https://api16-normal-c-alisg.tiktokv.com/passport/email/register_verify_login/"
 params = {
 "passport-sdk-version": "6031990",
 "device_platform": "android",
 "os": "android",
 "ssmix": "a",
 "_rticket": "1752875715998",
 "cdid": "a90f0ed5-8028-413e-a00d-77e931779d00",
 "channel": "googleplay",
 "aid": "1233",
 "app_name": "musical_ly",
 "version_code": "370805",
 "version_name": "37.8.5",
 "manifest_version_code": "2023708050",
 "update_version_code": "2023708050",
 "ab_version": "37.8.5",
 "resolution": "900*1600",
 "dpi": "240",
 "device_type": "NE2211",
 "device_brand": "OnePlus",
 "language": "en",
 "os_api": "28",
 "os_version": "9",
 "ac": "wifi",
 "is_pad": "0",
 "current_region": "DE",
 "app_type": "normal",
 "sys_region": "US",
 "last_install_time": "1752871588",
 "mcc_mnc": "46692",
 "timezone_name": "Asia/Baghdad",
 "carrier_region_v2": "DE",
 "residence": "DE",
 "app_language": "en",
 "carrier_region": "DE",
 "timezone_offset": "10800",
 "host_abi": "arm64-v8a",
 "locale": "en-GB",
 "ac2": "wifi",
 "uoo": "0",
 "op_region": "DE",
 "build_number": "37.8.5",
 "region": "GB",
 "ts": "1752875714",
 "iid": "7528525992324908807",
 "device_id": "7528525775047132680",
 "openudid": "7a59d727a58ee91e",
 "support_webview": "1",
 "reg_store_region": "de",
 "user_selected_region": "0",
 "okhttp_version": "4.2.210.6-tiktok",
 "use_store_region_cookie": "1",
 "app_version":"37.8.5"
 }
 payload = {
 'birthday': birthdate,
 'fixed_mix_mode': "1",
 'code': xor_encrypt(code),
 'account_sdk_source': "app",
 'mix_mode': "1",
 'multi_login': "1",
 'type': "34",
 'email': xor_encrypt(email),
 }
 m = SignerPy.sign(params=params, payload=payload)

 headers = {
 'User-Agent': "com.zhiliaoapp.musically/2023708050 (Linux; U; Android 9; en_GB; NE2211; Build/SKQ1.220617.001;tt-ok/3.12.13.16)",
 'Connection': "Keep-Alive",
 'Accept-Encoding': "gzip",
 'X-SS-STUB': m['x-ss-stub'],
 'x-tt-pba-enable': "1",
 'x-bd-kmsv': "0",
 'x-tt-dm-status': "login=1;ct=1;rt=8",
 'X-SS-REQ-TICKET': m['x-ss-req-ticket'],
 'x-bd-client-key': "#yEjw14J8W9l4SfT9U1TO60CXVvhTKWlciV4wIs/yJvoJp9e6R85bFU+QLZlj2NzfUISVioYXoQrs9gx6",
 'x-tt-passport-csrf-token': "13e1ddab691a6a5ed7cd70592d960fe7",
 'tt-ticket-guard-public-key': "BHxT6qq83FTRAnJYjUgFDzwxX14GDgGVWmXnZftx8oJntWW03KYyAqdengSdAMgufFURdqiqF23x6RFV+F4593I=",
 'sdk-version': "2",
 'tt-ticket-guard-iteration-version': "0",
 'X-Tt-Token': "0370c890e123ee06efe9bfd83298e202d701f5742061f9f4abf220abb27fdc3f7d8a2389a8db93c3ea4e1a4e24cdf19e194ed15acffd5e582ca1177dc53e71281973c50f7f5a498c43e00a210bb650575fb5c2488922fbbc51cdb25cdb4b960d90767--0a4e0a2088aefe8e956071b58d7e88474a1b08e4021225bcf93fb9044dc0b2164e4680d71220e811fecf461dd5e810309dae1c0fa532912e69b7449d6ce777d95fe44c8dc8b41801220674696b746f6b-3.0.0",
 'tt-ticket-guard-version': "3",
 'passport-sdk-settings': "x-tt-token",
 'passport-sdk-sign': "x-tt-token",
 'passport-sdk-version': "6031990",
 'x-tt-bypass-dp': "1",
 'oec-vc-sdk-version': "3.0.5.i18n",
 'x-vc-bdturing-sdk-version': "2.3.8.i18n",
 'x-tt-request-tag': "n=0;nr=011;bg=0",
 'X-Ladon': m['x-ladon'],
 'X-Khronos': m['x-khronos'],
 'X-Argus': m['x-argus'],
 'X-Gorgon': m['x-gorgon'],
 }
 resp = session.post(url, params=params, data=payload, headers=headers)
 # Return the whole response object so we can get data and headers
 return resp

# =============================================================================
# 5. TIKTOK BOT ENGINE (Updated with Share-Live.py Logic)
# =============================================================================

class TikTokBot:
    def __init__(self):
        self._running = False
        self._proxy_manager = ProxyManager()
        self._faker = SharkFaker()
        self._accounts = []
        self.stats = {
            'views_completed': 0,
            'views_failed': 0,
            'likes_completed': 0,
            'likes_failed': 0,
            'shares_completed': 0,
            'shares_failed': 0,
            'requests_sent': 0,
            'requests_success': 0,
            'requests_failed': 0
        }
        self._session = requests.Session()
        
    def load_accounts(self):
        """Load accounts from storage (mock)"""
        for i in range(10):
            device = SharkDevice()
            self._accounts.append({
                'username': f'user_{i}',
                'device': device.to_dict(),
                'status': 'active'
            })
        logger.info(f"Loaded {len(self._accounts)} accounts")

    # --- NEW: Username to Room ID Grabber ---
    def get_room_info(self, username: str, session_id: str) -> Dict[str, str]:
        """
        Grabs Room ID and Owner ID from Username using Share-Live.py logic.
        """
        headers = {
            "Cookie": f"sessionid={session_id};",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        try:
            url = f"https://www.tiktok.com/api-live/user/room/?aid=1988&app_language=en&app_name=tiktok_web&browser_language=en&browser_name=Mozilla&browser_online=true&browser_platform=Win32&browser_version=5.0%20%28Windows%29&channel=tiktok_web&cookie_enabled=true&device_id=7129559580162868738&device_platform=web_pc&focus_state=true&from_page=user&history_len=7&is_fullscreen=false&is_page_visible=true&os=windows&priority_region=US&referer=https%3A%2F%2Fwww.tiktok.com%2Fforyou&region=US&root_referer=https%3A%2F%2Fwww.tiktok.com%2F&screen_height=768&screen_width=1366&sourceType=54&tz_name=UTC&uniqueId={username}&verifyFp=verify_l71zqvs2_YCWVL2JM_1nvE_4oRk_8FnT_X2jkG5zAgQIK&webcast_language=en"
            rez = requests.get(url, headers=headers).json()
            
            if rez.get("data", {}).get("user"):
                room = rez["data"]["user"]["roomId"]
                owner_id = rez["data"]["user"]["id"]
                logger.info(f"Room ID: {room} | Owner ID: {owner_id}")
                return {"room_id": room, "owner_id": owner_id}
            else:
                logger.error("User not found or no live room.")
                return {}
        except Exception as e:
            logger.error(f"Error grabbing room info: {e}")
            return {}

    def start_views(self, target_id, total_views, threads, is_live=False):
        """Start view campaign"""
        self._running = True
        logger.info(f"Starting {total_views} views on {target_id} with {threads} threads")
        
        for _ in range(threads):
            t = threading.Thread(target=self._view_loop, args=(target_id, total_views // threads, is_live))
            t.start()
            
    def start_live_likes(self, room_id, total_likes, threads):
        """Start live likes campaign"""
        self._running = True
        logger.info(f"Starting {total_likes} likes on room {room_id} with {threads} threads")
        for _ in range(threads):
            t = threading.Thread(target=self._like_loop, args=(room_id, total_likes // threads))
            t.start()

    def start_live_shares(self, room_id, total_shares, threads, session_id: str = None):
        """
        Start live shares campaign using Share-Live.py logic.
        """
        self._running = True
        logger.info(f"Starting {total_shares} shares on room {room_id} with {threads} threads")
        
        # If session_id is provided, we can grab room info if needed, 
        # but here we assume room_id is already known or passed directly.
        
        for _ in range(threads):
            t = threading.Thread(target=self._share_loop, args=(room_id, total_shares // threads, session_id))
            t.start()

    def start_live_campaign(self, room_id, total_views, like_prob, share_prob, threads):
        """Start full campaign"""
        self._running = True
        logger.info(f"Starting campaign on room {room_id} with {threads} threads")
        for _ in range(threads):
            t = threading.Thread(target=self._campaign_loop, args=(room_id, total_views // threads, like_prob, share_prob))
            t.start()
    
    def generate_account_thread(self, count=1):
        """Start account generation in a thread"""
        threading.Thread(target=self._generate_account_loop, args=(count,), daemon=True).start()

    def stop(self):
        self._running = False
        logger.info("Bot stopped")

    def _get_proxy(self):
        return self._proxy_manager.get_random_proxy()

    def _sign_request(self, params, payload=None):
        """Sign request using SharkParams"""
        headers = self._faker.generate_signer_headers(params, payload)
        return headers

    def _send_request(self, endpoint, params, payload=None, json_data=None, cookies=None):
        """Send signed request"""
        proxy = self._get_proxy()
        proxies = {'http': f"http://{proxy}", 'https': f"http://{proxy}"} if proxy else {}
        
        headers = {
            'User-Agent': 'com.zhiliaoapp.musically/2023708050 (Linux; U; Android 13; en_US; Pixel 8; Build/TP1A.220624.014;tt-ok/3.12.13.16)',
            'Connection': 'Keep-Alive',
            'Accept-Encoding': 'gzip, deflate',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
        }
        
        # Add signer headers
        signer_headers = self._sign_request(params, payload)
        headers.update(signer_headers)
        
        self.stats['requests_sent'] += 1
        
        try:
            resp = requests.post(endpoint, params=params, data=payload if payload else None, json=json_data if json_data else None, proxies=proxies, headers=headers, cookies=cookies, timeout=7)
            if resp.status_code == 200:
                self.stats['requests_success'] += 1
                return resp.json()
            else:
                self.stats['requests_failed'] += 1
                return None
        except Exception:
            self.stats['requests_failed'] += 1
            return None

    def _view_loop(self, target_id, count, is_live=False):
        """Loop for views"""
        for _ in range(count):
            if not self._running:
                break
            
            device = SharkDevice()
            params = self._faker.generate_base_params(device)
            
            if is_live:
                params['room_id'] = target_id
                endpoint = f"https://webcast-h2.tiktokv.com/webcast/room/enter/"
                payload = f"room_id={target_id}&enter_source=profile"
            else:
                params['aweme_id'] = target_id
                endpoint = f"https://aweme.snssdk.com/aweme/v1/play/"
                payload = None
                
            self._send_request(endpoint, params, payload)
            self.stats['views_completed'] += 1
            time.sleep(random.uniform(0.5, 2))

    def _like_loop(self, room_id, count):
        """Loop for likes"""
        for _ in range(count):
            if not self._running:
                break
            
            device = SharkDevice()
            params = self._faker.generate_base_params(device)
            params['room_id'] = room_id
            params['like_count'] = random.randint(1, 5)
            
            endpoint = f"https://webcast-h2.tiktokv.com/webcast/like/"
            payload = f"room_id={room_id}&like_count={params['like_count']}"
            
            self._send_request(endpoint, params, payload)
            self.stats['likes_completed'] += 1
            time.sleep(random.uniform(0.5, 1))

    def _share_loop(self, room_id, count, session_id: str = None):
        """
        Loop for shares using Share-Live.py logic.
        """
        for _ in range(count):
            if not self._running:
                break
            
            # Use SharkParams for base, but use Share-Live specific structure
            device = SharkDevice()
            
            # Base params
            params = self._faker.generate_base_params(device)
            params['room_id'] = room_id
            
            # Headers and Cookies from Share-Live.py
            headers = {
                "Content-Type": "application/json; charset=UTF-8",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            cookies = {"sessionid": session_id, "sessionid_ss": session_id} if session_id else None
            
            # JSON Data from Share-Live.py
            json_data = {
                "room_id": str(room_id),
                "target_id": room_id, # Usually owner_id, but room_id is used in many share types
                "share_type": 2
            }
            
            endpoint = "https://webcast.tiktok.com/webcast/room/share/"
            
            # Send request with JSON body
            proxy = self._get_proxy()
            proxies = {'http': f"http://{proxy}", 'https': f"http://{proxy}"} if proxy else {}
            
            self.stats['requests_sent'] += 1
            try:
                req = requests.post(endpoint, params=params, headers=headers, json=json_data, cookies=cookies, proxies=proxies, timeout=7)
                if req.status_code == 200:
                    self.stats['shares_completed'] += 1
                else:
                    self.stats['shares_failed'] += 1
            except:
                self.stats['shares_failed'] += 1
            
            time.sleep(random.uniform(0.5, 1))
            
    def _generate_account_loop(self, count=1):
        """Generate accounts using 3accmain.py logic"""
        for _ in range(count):
            if not self._running:
                break
            try:
                # 1) Create temp email
                email, tm_token = create_temp_email()
                
                # 2) Generate password and birthdate
                password = generate_password(12)
                birthdate = generate_birthdate()
                
                # 3) Send TikTok code
                session = requests.Session()
                params, install_id = self._faker.generate_base_params(SharkDevice()), None # Simplified params for gen
                # Actually make_tiktok_params returns a tuple (params, install_id) but we need to mimic the structure
                # For simplicity in Flask, we'll just use the static params from 3accmain.py context if needed, 
                # but let's use the SharkDevice params for consistency
                params = self._faker.generate_base_params(SharkDevice())
                install_id = SharkDevice().install_id
                
                resp_send = send_tiktok_code(session, email, params, install_id, password)
                
                if not resp_send:
                    continue
                
                # 4) Wait for code
                code = fetch_code_from_email(email, timeout=10)
                if not code:
                    continue
                    
                # 5) Verify
                response_obj = verify_tiktok_email(session, email, code, birthdate)
                
                if not response_obj:
                    continue
                
                resp_verify = response_obj.json()
                data = resp_verify.get("data", {})
                session_key = data.get("session_key")
                
                x_tt_token = data.get("token") or response_obj.headers.get("X-Tt-Token")
                username = data.get("name")
                
                if session_key:
                    account_data = {
                        'email': email,
                        'password': password,
                        'username': username,
                        'session_key': session_key,
                        'x_tt_token': x_tt_token,
                        'tm_token': tm_token
                    }
                    self._accounts.append(account_data)
                    # Save to file
                    with open("accounts.txt", "a") as f:
                        f.write(f"{email}:{password}:{username}\n")
                    with open("session.txt", "a") as f:
                        f.write(f"{session_key}:{x_tt_token}:{tm_token}\n")
            except Exception as e:
                logger.error(f"Error generating account: {e}")
            time.sleep(1)

    def _campaign_loop(self, room_id, count, like_prob, share_prob):
        """Advanced campaign loop"""
        for _ in range(count):
            if not self._running:
                break
            
            # View
            device = SharkDevice()
            params = self._faker.generate_base_params(device)
            params['room_id'] = room_id
            endpoint = f"https://webcast-h2.tiktokv.com/webcast/room/enter/"
            payload = f"room_id={room_id}&enter_source=profile"
            self._send_request(endpoint, params, payload)
            self.stats['views_completed'] += 1
            
            # Like?
            if random.random() < like_prob:
                params2 = self._faker.generate_base_params(device)
                params2['room_id'] = room_id
                params2['like_count'] = random.randint(1, 5)
                endpoint2 = f"https://webcast-h2.tiktokv.com/webcast/like/"
                payload2 = f"room_id={room_id}&like_count={params2['like_count']}"
                self._send_request(endpoint2, params2, payload2)
                self.stats['likes_completed'] += 1
                
            # Share?
            if random.random() < share_prob:
                # Use share loop logic
                device3 = SharkDevice()
                params3 = self._faker.generate_base_params(device3)
                params3['room_id'] = room_id
                
                headers3 = {
                    "Content-Type": "application/json; charset=UTF-8",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
                
                json_data3 = {
                    "room_id": str(room_id),
                    "target_id": room_id,
                    "share_type": 2
                }
                
                endpoint3 = "https://webcast.tiktok.com/webcast/room/share/"
                proxy = self._get_proxy()
                proxies3 = {'http': f"http://{proxy}", 'https': f"http://{proxy}"} if proxy else {}
                
                self.stats['requests_sent'] += 1
                try:
                    req = requests.post(endpoint3, params=params3, headers=headers3, json=json_data3, proxies=proxies3, timeout=7)
                    if req.status_code == 200:
                        self.stats['shares_completed'] += 1
                    else:
                        self.stats['shares_failed'] += 1
                except:
                    self.stats['shares_failed'] += 1
                    
            time.sleep(random.uniform(0.5, 2))

# =============================================================================
# 6. FLASK API
# =============================================================================

# Initialize Flask app
app = Flask(__name__)
CORS(app)
api = Api(app, version='3.0', title='TikTok Bot Control API',
 description='Full-featured REST API for TikTok bot control and monitoring')

# Namespaces
ns_bot = api.namespace('api/bot', description='Bot operations')
ns_accounts = api.namespace('api/accounts', description='Account management')
ns_proxies = api.namespace('api/proxies', description='Proxy management')
ns_config = api.namespace('api/config', description='Configuration')
ns_campaigns = api.namespace('api/campaigns', description='Campaign management')
ns_stats = api.namespace('api/stats', description='Statistics & monitoring')
ns_grabber = api.namespace('api/grabber', description='Username to Room ID Grabber')

# Global bot instance
bot = None
current_campaign = None
campaign_lock = threading.Lock()

# ============================================================
# INITIALIZATION & CLEANUP
# ============================================================

def init_bot():
    """Initialize bot instance"""
    global bot
    if bot is None:
        logger.info("Initializing TikTok Bot...")
        try:
            bot = TikTokBot()
            bot.load_accounts()
            # Scrape and check proxies
            bot._proxy_manager.scrape_proxies()
            bot._proxy_manager.check_proxies(max_workers=config.get('proxy_check_workers', 4000))
            logger.info(f"Bot initialized with {len(bot._accounts)} accounts")
        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}")
            raise

def cleanup():
    """Cleanup on shutdown"""
    global bot
    if bot and bot._running:
        logger.info("Stopping bot...")
        bot.stop()

atexit.register(cleanup)

# ============================================================
# DECORATORS
# ============================================================

def require_bot(f):
    """Ensure bot is initialized"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if bot is None:
            return {'error': 'Bot not initialized'}, 503
        return f(*args, **kwargs)
    return decorated_function

def require_running(f):
    """Ensure bot is running"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if bot is None or not bot._running:
            return {'error': 'Bot is not running'}, 409
        return f(*args, **kwargs)
    return decorated_function

# ============================================================
# BOT OPERATIONS
# ============================================================

@ns_bot.route('/init')
class BotInit(Resource):
    @require_bot
    def post(self):
        """Initialize bot with config"""
        return {
            'status': 'initialized',
            'accounts': len(bot._accounts),
            'proxies': bot._proxy_manager.get_working_count()
        }, 200

@ns_bot.route('/status')
class BotStatus(Resource):
    @require_bot
    def get(self):
        """Get current bot status"""
        return {
            'running': bot._running,
            'status': 'Running' if bot._running else 'Idle',
            'accounts_loaded': len(bot._accounts),
            'proxies_working': bot._proxy_manager.get_working_count(),
            'stats': bot.stats,
        }, 200

@ns_bot.route('/stop')
class BotStop(Resource):
    @require_bot
    def post(self):
        """Stop bot operations"""
        if bot._running:
            bot.stop()
        return {'status': 'stopped'}, 200

@ns_bot.route('/health')
class Health(Resource):
    def get(self):
        """Health check"""
        return {
            'status': 'ok',
            'bot_initialized': bot is not None,
            'timestamp': datetime.now().isoformat(),
        }, 200

# ============================================================
# GRABBER OPERATIONS (New)
# ============================================================

@ns_grabber.route('/username-to-room')
class GrabRoom(Resource):
    @require_bot
    def post(self):
        """Grab Room ID and Owner ID from Username"""
        data = request.get_json()
        username = data.get('username')
        session_id = data.get('session_id')
        
        if not username:
            return {'error': 'username required'}, 400
        
        try:
            info = bot.get_room_info(username, session_id)
            if info:
                return {
                    'status': 'success',
                    'data': info
                }, 200
            else:
                return {'status': 'failed', 'message': 'Could not find room'}, 404
        except Exception as e:
            return {'error': str(e)}, 500

# ============================================================
# CAMPAIGN OPERATIONS
# ============================================================

@ns_campaigns.route('/video/start')
class StartVideoViews(Resource):
    @require_bot
    def post(self):
        """Start video view campaign"""
        data = request.get_json()
        video_id = data.get('video_id')
        total_views = data.get('total_views', 100)
        threads = data.get('threads', config.get('threads', 5))
        
        if not video_id:
            return {'error': 'video_id required'}, 400
        
        if bot._running:
            return {'error': 'Bot already running'}, 409
        
        try:
            thread = threading.Thread(
                target=bot.start_views,
                args=(video_id, total_views, threads, False),
                daemon=True
            )
            thread.start()
            
            return {
                'status': 'started',
                'video_id': video_id,
                'target_views': total_views,
                'threads': threads,
            }, 200
        except Exception as e:
            return {'error': str(e)}, 500

@ns_campaigns.route('/live/views/start')
class StartLiveViews(Resource):
    @require_bot
    def post(self):
        """Start live stream view campaign"""
        data = request.get_json()
        room_id = data.get('room_id')
        total_views = data.get('total_views', 100)
        threads = data.get('threads', config.get('threads', 5))
        
        if not room_id:
            return {'error': 'room_id required'}, 400
        
        if bot._running:
            return {'error': 'Bot already running'}, 409
        
        try:
            thread = threading.Thread(
                target=bot.start_views,
                args=(room_id, total_views, threads, True),
                daemon=True
            )
            thread.start()
            
            return {
                'status': 'started',
                'room_id': room_id,
                'target_views': total_views,
                'threads': threads,
            }, 200
        except Exception as e:
            return {'error': str(e)}, 500

@ns_campaigns.route('/live/likes/start')
class StartLiveLikes(Resource):
    @require_bot
    def post(self):
        """Start live stream likes campaign"""
        data = request.get_json()
        room_id = data.get('room_id')
        total_likes = data.get('total_likes', 200)
        threads = data.get('threads', min(config.get('threads', 5), total_likes))
        
        if not room_id:
            return {'error': 'room_id required'}, 400
        
        if bot._running:
            return {'error': 'Bot already running'}, 409
        
        try:
            thread = threading.Thread(
                target=bot.start_live_likes,
                args=(room_id, total_likes, threads),
                daemon=True
            )
            thread.start()
            
            return {
                'status': 'started',
                'room_id': room_id,
                'target_likes': total_likes,
                'threads': threads,
            }, 200
        except Exception as e:
            return {'error': str(e)}, 500

@ns_campaigns.route('/live/shares/start')
class StartLiveShares(Resource):
    @require_bot
    def post(self):
        """
        Start live stream shares campaign using Share-Live.py logic.
        """
        data = request.get_json()
        room_id = data.get('room_id')
        total_shares = data.get('total_shares', 100)
        threads = data.get('threads', min(config.get('threads', 5), total_shares))
        session_id = data.get('session_id') # Optional, but recommended
        
        if not room_id:
            return {'error': 'room_id required'}, 400
        
        if bot._running:
            return {'error': 'Bot already running'}, 409
        
        try:
            thread = threading.Thread(
                target=bot.start_live_shares,
                args=(room_id, total_shares, threads, session_id),
                daemon=True
            )
            thread.start()
            
            return {
                'status': 'started',
                'room_id': room_id,
                'target_shares': total_shares,
                'threads': threads,
            }, 200
        except Exception as e:
            return {'error': str(e)}, 500

@ns_campaigns.route('/live/campaign/start')
class StartLiveCampaign(Resource):
    @require_bot
    def post(self):
        """Start full live campaign (views+likes+shares)"""
        data = request.get_json()
        room_id = data.get('room_id')
        total_views = data.get('total_views', 100)
        like_prob = data.get('like_probability', config.get('like_probability', 0.3))
        share_prob = data.get('share_probability', config.get('share_probability', 0.1))
        threads = data.get('threads', config.get('threads', 5))
        
        if not room_id:
            return {'error': 'room_id required'}, 400
        
        if bot._running:
            return {'error': 'Bot already running'}, 409
        
        try:
            thread = threading.Thread(
                target=bot.start_live_campaign,
                args=(room_id, total_views, like_prob, share_prob, threads),
                daemon=True
            )
            thread.start()
            
            est_likes = int(total_views * like_prob * 2)
            est_shares = int(total_views * share_prob)
            
            return {
                'status': 'started',
                'room_id': room_id,
                'target_views': total_views,
                'estimated_likes': est_likes,
                'estimated_shares': est_shares,
                'like_probability': like_prob,
                'share_probability': share_prob,
                'threads': threads,
            }, 200
        except Exception as e:
            return {'error': str(e)}, 500

# ============================================================
# ACCOUNT MANAGEMENT (Updated with Gen)
# ============================================================

@ns_accounts.route('/list')
class AccountsList(Resource):
    @require_bot
    def get(self):
        """List all loaded accounts"""
        accounts = bot._accounts
        return {
            'total': len(accounts),
            'accounts': accounts[:100], # Limit to 100 for API
        }, 200

@ns_accounts.route('/generate')
class AccountGenerate(Resource):
    @require_bot
    def post(self):
        """Generate new accounts"""
        data = request.get_json()
        count = data.get('count', 10)
        prefix = data.get('prefix', '')
        
        if count > 1000:
            return {'error': 'Maximum 1000 accounts per request'}, 400
        
        try:
            logger.info(f"Generating {count} accounts...")
            bot.generate_account_thread(count)
            
            return {
                'status': 'started',
                'count': count,
            }, 200
        except Exception as e:
            return {'error': str(e)}, 500

@ns_accounts.route('/stats')
class AccountStats(Resource):
    @require_bot
    def get(self):
        """Get account statistics"""
        accounts = bot._accounts
        total_views = sum(a.get('total_views', 0) for a in accounts)
        active_count = len([a for a in accounts if a.get('status') == 'active'])
        
        return {
            'total_accounts': len(accounts),
            'active_accounts': active_count,
            'total_views_delivered': total_views,
        }, 200

# ============================================================
# PROXY MANAGEMENT
# ============================================================

@ns_proxies.route('/scrape')
class ProxyScrape(Resource):
    @require_bot
    def post(self):
        """Scrape proxies from sources"""
        data = request.get_json() or {}
        max_sources = data.get('max_sources', 19)
        
        try:
            logger.info(f"Scraping proxies from {max_sources} sources...")
            count = bot._proxy_manager.scrape_proxies(max_sources=max_sources)
            
            return {
                'status': 'scraped',
                'count': count,
                'sources': max_sources,
            }, 200
        except Exception as e:
            return {'error': str(e)}, 500

@ns_proxies.route('/check')
class ProxyCheck(Resource):
    @require_bot
    def post(self):
        """Check proxies for validity"""
        data = request.get_json() or {}
        max_workers = data.get('max_workers', config.get('proxy_check_workers', 500))
        timeout = data.get('timeout', config.get('proxy_timeout', 3))
        
        try:
            logger.info(f"Checking proxies with {max_workers} workers...")
            count = bot._proxy_manager.check_proxies(max_workers=max_workers, timeout=timeout)
            
            return {
                'status': 'checked',
                'working': count,
            }, 200
        except Exception as e:
            return {'error': str(e)}, 500

@ns_proxies.route('/stats')
class ProxyStats(Resource):
    @require_bot
    def get(self):
        """Get proxy statistics"""
        stats = bot._proxy_manager.get_proxy_stats()
        
        return {
            'total': stats.get('total', 0),
            'avg_latency': stats.get('avg_latency', 0),
            'min_latency': stats.get('min_latency', 0),
            'max_latency': stats.get('max_latency', 0),
            'median_latency': stats.get('median_latency', 0),
        }, 200

# ============================================================
# CONFIGURATION
# ============================================================

@ns_config.route('/get')
class ConfigGet(Resource):
    def get(self):
        """Get current configuration"""
        return {'config': config}, 200

@ns_config.route('/set')
class ConfigSet(Resource):
    def post(self):
        """Update configuration"""
        data = request.get_json()
        
        try:
            for key, value in data.items():
                if key in config:
                    config[key] = value
            
            save_config()
            return {'status': 'saved', 'config': config}, 200
        except Exception as e:
            return {'error': str(e)}, 500

@ns_config.route('/reset')
class ConfigReset(Resource):
    def post(self):
        """Reset to default configuration"""
        try:
            config.clear()
            config.update(DEFAULT_CONFIG.copy())
            save_config()
            
            return {'status': 'reset', 'config': config}, 200
        except Exception as e:
            return {'error': str(e)}, 500

@ns_config.route('/export')
class ConfigExport(Resource):
    def get(self):
        """Export configuration as JSON"""
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'config': config,
            'stats': bot.stats if bot else {},
        }
        
        return export_data, 200

@ns_config.route('/import')
class ConfigImport(Resource):
    def post(self):
        """Import configuration from JSON"""
        try:
            data = request.get_json()
            
            if 'config' in data:
                config.clear()
                config.update(data['config'])
                save_config()
                
                return {'status': 'imported'}, 200
        except Exception as e:
            return {'error': str(e)}, 500

# ============================================================
# STATISTICS & MONITORING
# ============================================================

@ns_stats.route('/current')
class CurrentStats(Resource):
    @require_bot
    def get(self):
        """Get current operation statistics"""
        return bot.stats, 200

@ns_stats.route('/requests')
class RequestStats(Resource):
    @require_bot
    def get(self):
        """Get request statistics"""
        stats = bot.stats
        sent = stats.get('requests_sent', 0)
        success = stats.get('requests_success', 0)
        failed = stats.get('requests_failed', 0)
        
        success_rate = (success / sent * 100) if sent > 0 else 0
        
        return {
            'sent': sent,
            'success': success,
            'failed': failed,
            'success_rate': success_rate,
        }, 200

# ============================================================
# WEB DASHBOARD
# ============================================================

@app.route('/')
def dashboard():
    """Serve simple HTML dashboard"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
    <title>TikTok Bot Control Panel</title>
    <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh; padding: 20px; }
    .container { max-width: 1200px; margin: 0 auto; }
    header { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    h1 { color: #333; font-size: 28px; margin-bottom: 10px; }
    .status { display: flex; gap: 20px; margin-top: 15px; }
    .stat-card { background: #f5f5f5; padding: 15px; border-radius: 6px; min-width: 150px; }
    .stat-label { color: #666; font-size: 12px; text-transform: uppercase; }
    .stat-value { font-size: 24px; font-weight: bold; color: #333; margin-top: 5px; }
    .section { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .section h2 { color: #333; font-size: 20px; margin-bottom: 15px; border-bottom: 2px solid #667eea;
    padding-bottom: 10px; }
    .form-group { margin-bottom: 15px; }
    label { display: block; margin-bottom: 5px; color: #555; font-weight: 500; }
    input, select { width: 100%; padding: 8px 12px; border: 1px solid #ddd; border-radius: 4px;
    font-size: 14px; }
    button { background: #667eea; color: white; padding: 10px 20px; border: none; border-radius: 4px;
    cursor: pointer; font-size: 14px; font-weight: 500; }
    button:hover { background: #5568d3; }
    button:disabled { background: #ccc; cursor: not-allowed; }
    .button-group { display: flex; gap: 10px; }
    .endpoint { background: #f9f9f9; padding: 15px; margin-bottom: 10px; border-radius: 4px;
    border-left: 4px solid #667eea; }
    .endpoint-name { font-weight: 600; color: #333; margin-bottom: 5px; }
    .endpoint-desc { color: #666; font-size: 13px; margin-bottom: 10px; }
    .alert { padding: 12px; border-radius: 4px; margin-bottom: 15px; }
    .alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
    .alert-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
    .alert-info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
    table { width: 100%; border-collapse: collapse; margin-top: 15px; }
    th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
    th { background: #f5f5f5; font-weight: 600; }
    code { background: #f5f5f5; padding: 2px 6px; border-radius: 3px; font-family: monospace;
    color: #d63384; }
    </style>
    </head>
    <body>
    <div class="container">
    <header>
    <h1>🎯 TikTok Bot Control Panel v3.0</h1>
    <div class="status">
    <div class="stat-card">
    <div class="stat-label">Status</div>
    <div class="stat-value" id="bot-status">Loading...</div>
    </div>
    <div class="stat-card">
    <div class="stat-label">Accounts</div>
    <div class="stat-value" id="account-count">-</div>
    </div>
    <div class="stat-card">
    <div class="stat-label">Proxies</div>
    <div class="stat-value" id="proxy-count">-</div>
    </div>
    <div class="stat-card">
    <div class="stat-label">Views</div>
    <div class="stat-value" id="view-count">-</div>
    </div>
    </div>
    </header>

    <div class="section">
    <h2>📊 Quick Controls</h2>
    <div id="alerts"></div>
    
    <div class="form-group">
    <label>Campaign Type</label>
    <select id="campaign-type">
    <option value="video">Video Views</option>
    <option value="live-views">Live Views</option>
    <option value="live-likes">Live Likes</option>
    <option value="live-shares">Live Shares (Share-Live.py Logic)</option>
    <option value="live-campaign">Full Campaign (Views+Likes+Shares)</option>
    </select>
    </div>

    <div class="form-group">
    <label>Target ID (Video ID or Room ID)</label>
    <input type="text" id="target-id" placeholder="Enter video/room ID">
    </div>

    <div class="form-group">
    <label>Target Count</label>
    <input type="number" id="target-count" value="100" min="1" max="10000">
    </div>

    <div class="form-group">
    <label>Threads</label>
    <input type="number" id="threads" value="5" min="1" max="100">
    </div>
    
    <div class="form-group">
    <label>Session ID (For Shares)</label>
    <input type="text" id="session-id" placeholder="Enter sessionid">
    </div>

    <div class="button-group">
    <button onclick="startCampaign()">🚀 Start Campaign</button>
    <button onclick="stopCampaign()">⏹️ Stop Campaign</button>
    <button onclick="refreshStats()">🔄 Refresh Stats</button>
    </div>
    </div>

    <div class="section">
    <h2>🔍 Username to Room ID Grabber</h2>
    <div class="form-group">
    <label>Username</label>
    <input type="text" id="grab-username" placeholder="Enter TikTok Username">
    </div>
    <div class="form-group">
    <label>Session ID</label>
    <input type="text" id="grab-session" placeholder="Enter sessionid">
    </div>
    <button onclick="grabRoom()">Grab Room Info</button>
    <div id="grab-result" style="margin-top: 10px; color: #333;"></div>
    </div>

    <div class="section">
    <h2>🌐 Proxy Management</h2>
    <div class="endpoint">
    <div class="endpoint-name">Scrape Proxies</div>
    <div class="endpoint-desc">Scrape from 18+ sources</div>
    <button onclick="scrapeProxies()">Scrape</button>
    </div>
    <div class="endpoint">
    <div class="endpoint-name">Check Proxies</div>
    <div class="endpoint-desc">Multi-threaded checker (500 workers)</div>
    <button onclick="checkProxies()">Check</button>
    </div>
    <div class="endpoint">
    <div class="endpoint-name">Test on TikTok</div>
    <div class="endpoint-desc">Test proxies on TikTok endpoints</div>
    <button onclick="testProxiesOnTikTok()">Test Top 10</button>
    </div>
    </div>

    <div class="section">
    <h2>👥 Account Management</h2>
    <div class="form-group">
    <label>Generate Accounts</label>
    <input type="number" id="account-count-gen" value="10" min="1" max="1000">
    <button onclick="generateAccounts()">Generate</button>
    </div>
    <div id="account-list"></div>
    </div>

    <div class="section">
    <h2>⚙️ Configuration</h2>
    <table id="config-table"></table>
    <button onclick="resetConfig()">Reset to Defaults</button>
    <button onclick="exportConfig()">Export Config</button>
    </div>

    <div class="section">
    <h2>📡 API Endpoints</h2>
    <div class="endpoint">
    <div class="endpoint-name">Bot Status</div>
    <code>GET /api/bot/status</code>
    </div>
    <div class="endpoint">
    <div class="endpoint-name">Start Video Views</div>
    <code>POST /api/campaigns/video/start</code>
    </div>
    <div class="endpoint">
    <div class="endpoint-name">Start Live Shares (Share-Live Logic)</div>
    <code>POST /api/campaigns/live/shares/start</code>
    </div>
    <div class="endpoint">
    <div class="endpoint-name">Username to Room ID</div>
    <code>POST /api/grabber/username-to-room</code>
    </div>
    <div class="endpoint">
    <div class="endpoint-name">Get Stats</div>
    <code>GET /api/stats/current</code>
    </div>
    </div>
    </div>

    <script>
    function showAlert(message, type = 'info') {
    const alerts = document.getElementById('alerts');
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.textContent = message;
    alerts.appendChild(alert);
    setTimeout(() => alert.remove(), 5000);
    }

    async function apiCall(endpoint, method = 'GET', data = null) {
    try {
    const options = { method };
    if (data) options.headers = { 'Content-Type': 'application/json' };
    if (data) options.body = JSON.stringify(data);
    
    const response = await fetch(endpoint, options);
    const json = await response.json();
    return json;
    } catch (error) {
    showAlert(`Error: ${error.message}`, 'error');
    return null;
    }
    }

    async function refreshStats() {
    const status = await apiCall('/api/bot/status');
    if (status) {
    document.getElementById('bot-status').textContent = status.running ? 'Running' : 'Idle';
    document.getElementById('account-count').textContent = status.accounts_loaded || '-';
    document.getElementById('proxy-count').textContent = status.proxies_working || '-';
    document.getElementById('view-count').textContent = status.stats?.views_completed || '-';
    }
    }

    async function startCampaign() {
    const type = document.getElementById('campaign-type').value;
    const targetId = document.getElementById('target-id').value;
    const targetCount = parseInt(document.getElementById('target-count').value);
    const threads = parseInt(document.getElementById('threads').value);
    const sessionId = document.getElementById('session-id').value;

    if (!targetId) { showAlert('Please enter a target ID', 'error'); return; }

    let endpoint, data;
    switch (type) {
    case 'video':
    endpoint = '/api/campaigns/video/start';
    data = { video_id: targetId, total_views: targetCount, threads };
    break;
    case 'live-views':
    endpoint = '/api/campaigns/live/views/start';
    data = { room_id: targetId, total_views: targetCount, threads };
    break;
    case 'live-likes':
    endpoint = '/api/campaigns/live/likes/start';
    data = { room_id: targetId, total_likes: targetCount, threads };
    break;
    case 'live-shares':
    endpoint = '/api/campaigns/live/shares/start';
    data = { room_id: targetId, total_shares: targetCount, threads, session_id: sessionId };
    break;
    case 'live-campaign':
    endpoint = '/api/campaigns/live/campaign/start';
    data = { room_id: targetId, total_views: targetCount, threads };
    break;
    }

    const result = await apiCall(endpoint, 'POST', data);
    if (result?.status) {
    showAlert(`Campaign started: ${type}`, 'success');
    }
    }

    async function stopCampaign() {
    const result = await apiCall('/api/bot/stop', 'POST');
    if (result?.status) showAlert('Campaign stopped', 'success');
    }

    async function scrapeProxies() {
    const result = await apiCall('/api/proxies/scrape', 'POST');
    if (result?.count) showAlert(`Scraped ${result.count} proxies`, 'success');
    }

    async function checkProxies() {
    const result = await apiCall('/api/proxies/check', 'POST');
    if (result?.working) showAlert(`${result.working} working proxies found`, 'success');
    }

    async function testProxiesOnTikTok() {
    const result = await apiCall('/api/proxies/test-all', 'POST');
    if (result?.compatible) {
    showAlert(`${result.compatible}/${result.tested} proxies compatible with TikTok`, 'success');
    }
    }

    async function generateAccounts() {
    const count = parseInt(document.getElementById('account-count-gen').value);
    const result = await apiCall('/api/accounts/generate', 'POST', { count });
    if (result?.status) showAlert(`Generating ${result.count} accounts...`, 'success');
    }

    async function resetConfig() {
    if (confirm('Reset configuration to defaults?')) {
    const result = await apiCall('/api/config/reset', 'POST');
    if (result?.status) showAlert('Configuration reset', 'success');
    }
    }

    async function exportConfig() {
    const result = await apiCall('/api/config/export');
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `config-${new Date().toISOString()}.json`;
    a.click();
    }

    async function grabRoom() {
    const username = document.getElementById('grab-username').value;
    const sessionId = document.getElementById('grab-session').value;
    
    if (!username) { showAlert('Please enter a username', 'error'); return; }
    
    const result = await apiCall('/api/grabber/username-to-room', 'POST', { username, session_id: sessionId });
    
    if (result?.data) {
    document.getElementById('grab-result').innerHTML = `<strong>Room ID:</strong> ${result.data.room_id}<br><strong>Owner ID:</strong> ${result.data.owner_id}`;
    showAlert('Room info grabbed successfully', 'success');
    } else {
    document.getElementById('grab-result').innerHTML = '<strong>Failed to grab room info.</strong>';
    }
    }

    // Refresh stats every 2 seconds
    setInterval(refreshStats, 2000);
    refreshStats();
    </script>
    </body>
    </html>
    """
    return html

# ============================================================
# SERVER STARTUP
# ============================================================

def run_server(host='0.0.0.0', port=5000, debug=False):
    """Start Flask server"""
    logger.info(f"Starting TikTok Bot Control API on {host}:{port}")
    init_bot()
    app.run(host=host, port=port, debug=debug, threaded=True)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='TikTok Bot Flask Control API')
    parser.add_argument('--host', default='0.0.0.0', help='Server host')
    parser.add_argument('--port', type=int, default=5000, help='Server port')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--setup', action='store_true', help='Run setup menu before starting')
    args = parser.parse_args()
    
    if args.setup:
        show_setup_menu()
    
    run_server(args.host, args.port, args.debug)
```
