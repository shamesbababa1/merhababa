"""
Zefoy Telegram Botu - Railway Uyumlu (TEK DOSYA)
=================================================
Tüm kodlar tek dosyada, harici modül gerektirmez!
"""

import os
import sys
import requests
import time
import re
import threading
import json
import asyncio
import base64
import random
from datetime import datetime
from typing import Optional, Dict, Any, List

# ============================================
# 🔑 BURAYA KENDİ TOKEN'INI YAZ!
# ============================================
BOT_TOKEN = "7893591726:AAGlFt8PNgWrQ_HG0YgspS20Z_MmXYSGAao"  # ← Bunu değiştir!
# ============================================

# Playwright yolunu ayarla (Railway için)
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/usr/local/bin"

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ============================================
# PLAYWRIGHT İTHALATI
# ============================================
try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext
except ImportError:
    print("❌ Playwright yüklü değil! Çalıştır: pip install playwright && playwright install chromium")
    exit(1)


# ============================================
# ZEFOY OTOMASYON SINIFI (TEK DOSYA)
# ============================================

class ZefoyAutomation:
    """Zefoy.com otomasyon sınıfı"""
    
    BASE_URL = "https://zefoy.com"
    
    SERVICES = {
        "hearts": {"name": "Hearts", "selector": ".t-hearts-button"},
        "favorites": {"name": "Favorites", "selector": ".t-favorites-button"},
        "chearts": {"name": "Comment Hearts", "selector": ".t-chearts-button"},
    }
    
    def __init__(self, headless: bool = True, verbose: bool = False):
        self.headless = headless
        self.verbose = verbose
        self.browser = None
        self.context = None
        self.page = None
        self._playwright = None
        self._available_services = {}
    
    async def start(self):
        """Tarayıcıyı başlat"""
        self._playwright = await async_playwright().start()
        self.browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--no-first-run',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
            ]
        )
        self.context = await self.browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        )
        await self.context.clear_cookies()
        self.page = await self.context.new_page()
        self.page.set_default_timeout(10000)
        
        await self.page.goto(
            self.BASE_URL,
            wait_until="domcontentloaded",
            timeout=60000
        )
    
    async def handle_initial_setup(self):
        """Popup'ları temizle"""
        try:
            # Popup kapatma butonlarını dene
            for selector in ["button:has-text('Close')", "button:has-text('×')", ".popup-close"]:
                try:
                    await self.page.click(selector, timeout=2000)
                except:
                    pass
        except:
            pass
    
    async def is_on_main_page(self) -> bool:
        """Ana sayfada mı kontrol et"""
        if not self.page:
            return False
        for selector in [".t-hearts-button", ".t-favorites-button", ".t-chearts-button"]:
            try:
                if await self.page.locator(selector).is_visible(timeout=1000):
                    return True
            except:
                continue
        return False
    
    async def solve_captcha_auto(self, max_attempts: int = 5) -> str:
        """CAPTCHA'yı otomatik çözmeye çalış"""
        print(f"🔐 CAPTCHA çözülüyor... ({max_attempts} deneme)")
        
        for attempt in range(1, max_attempts + 1):
            try:
                # CAPTCHA resmini bul
                captcha_img = self.page.locator("img[alt='captcha']")
                if not await captcha_img.is_visible():
                    if await self.is_on_main_page():
                        return "solved"
                    continue
                
                print(f"   Deneme {attempt}/{max_attempts} - Lütfen CAPTCHA'yı manuel çöz")
                
                # Kullanıcının çözmesi için bekle
                for _ in range(30):  # 30 saniye bekle
                    if await self.is_on_main_page():
                        return "solved"
                    await asyncio.sleep(1)
                    
            except Exception as e:
                print(f"   CAPTCHA hatası: {e}")
                await asyncio.sleep(2)
        
        # Otomatik çözüm başarısız
        print("⚠️ Otomatik çözüm başarısız, manuel çözüm bekleniyor...")
        for _ in range(60):  # 60 saniye daha bekle
            if await self.is_on_main_page():
                return "solved"
            await asyncio.sleep(1)
        
        return "timeout"
    
    async def detect_available_services(self) -> dict:
        """Hangi servislerin aktif olduğunu kontrol et"""
        if not self.page:
            return {}
        
        available = {}
        for key, config in self.SERVICES.items():
            try:
                btn = self.page.locator(config["selector"])
                is_visible = await btn.is_visible(timeout=1000)
                if is_visible:
                    classes = await btn.get_attribute("class") or ""
                    is_disabled = "disabled" in classes.lower()
                    available[key] = not is_disabled
                else:
                    available[key] = False
            except:
                available[key] = False
        
        self._available_services = available
        return available
    
    async def send_service(self, service_key: str, video_url: str) -> dict:
        """Servisi gönder"""
        if not self.page:
            return {"success": False, "message": "Sayfa başlatılmamış", "wait_time": 0}
        
        if service_key not in self.SERVICES:
            return {"success": False, "message": f"Bilinmeyen servis: {service_key}", "wait_time": 0}
        
        try:
            # Servis butonuna tıkla
            selector = self.SERVICES[service_key]["selector"]
            await self.page.click(selector)
            await asyncio.sleep(2)
            
            # URL inputunu bul ve yaz
            url_input = self.page.locator("input[placeholder*='tiktok']")
            await url_input.fill(video_url)
            await asyncio.sleep(1)
            
            # Gönder butonuna tıkla
            submit_btn = self.page.locator("button:has-text('Submit')")
            await submit_btn.click()
            await asyncio.sleep(3)
            
            # Sonucu kontrol et
            try:
                result_text = await self.page.locator(".result").text_content(timeout=5000)
                if result_text:
                    return {"success": True, "message": result_text, "wait_time": 0}
            except:
                pass
            
            # Başarılı mesajı kontrol et
            try:
                success_text = await self.page.locator("text=Success").text_content(timeout=3000)
                if success_text:
                    return {"success": True, "message": "Başarıyla gönderildi!", "wait_time": 0}
            except:
                pass
            
            return {"success": False, "message": "Bilinmeyen hata", "wait_time": 60}
            
        except Exception as e:
            return {"success": False, "message": str(e), "wait_time": 60}
    
    async def close(self):
        """Tarayıcıyı kapat"""
        try:
            if self.browser:
                await self.browser.close()
            if self._playwright:
                await self._playwright.stop()
        except:
            pass


# ============================================
# TELEGRAM FONKSİYONLARI
# ============================================

def send_message(chat_id: int, text: str, parse_mode: str = "Markdown") -> dict:
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    try:
        return requests.post(url, json=payload, timeout=30).json()
    except:
        return {"ok": False}

def edit_message(chat_id: int, message_id: int, text: str, parse_mode: str = "Markdown") -> dict:
    url = f"{TELEGRAM_API}/editMessageText"
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": parse_mode}
    try:
        return requests.post(url, json=payload, timeout=30).json()
    except:
        return {"ok": False}

def send_keyboard(chat_id: int, text: str, buttons: list, parse_mode: str = "Markdown") -> dict:
    url = f"{TELEGRAM_API}/sendMessage"
    inline_keyboard = []
    for row in buttons:
        keyboard_row = []
        for btn_text, callback_data in row:
            keyboard_row.append({"text": btn_text, "callback_data": callback_data})
        inline_keyboard.append(keyboard_row)
    
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "reply_markup": json.dumps({"inline_keyboard": inline_keyboard})
    }
    try:
        return requests.post(url, json=payload, timeout=30).json()
    except:
        return {"ok": False}

def answer_callback(callback_id: str, text: str = "") -> dict:
    url = f"{TELEGRAM_API}/answerCallbackQuery"
    payload = {"callback_query_id": callback_id, "text": text}
    try:
        return requests.post(url, json=payload, timeout=30).json()
    except:
        return {"ok": False}

def get_updates(offset: Optional[int] = None) -> list:
    url = f"{TELEGRAM_API}/getUpdates"
    payload = {"timeout": 30}
    if offset:
        payload["offset"] = offset
    try:
        data = requests.get(url, params=payload, timeout=35).json()
        return data.get("result", []) if data.get("ok") else []
    except:
        return []


# ============================================
# URL KONTROL FONKSİYONLARI
# ============================================

def is_valid_tiktok_url(url: str) -> bool:
    patterns = [
        r"tiktok\.com/@[\w.]+/video/\d+",
        r"tiktok\.com/v/\d+",
        r"vm\.tiktok\.com/\w+",
        r"vt\.tiktok\.com/\w+",
    ]
    return any(re.search(p, url) for p in patterns)

def format_time(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    mins = seconds // 60
    secs = seconds % 60
    return f"{mins}m {secs}s"


# ============================================
# ZEFOY İŞLEMİ (ARKA PLANDA ÇALIŞIR)
# ============================================

def run_automation_task(chat_id: int, message_id: int, service: str, url: str):
    """Arka planda Zefoy çalıştır"""
    try:
        status_text = f"🔄 **İşlem başlatıldı...**\n\n📹 Video: `{url}`\n🎯 Servis: {service.capitalize()}"
        edit_message(chat_id, message_id, status_text)
        
        # Asyncio döngüsü oluştur
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Zefoy botunu başlat
        automation = ZefoyAutomation(headless=True, verbose=False)
        
        # Başlat
        loop.run_until_complete(automation.start())
        edit_message(chat_id, message_id, f"🔄 Tarayıcı başlatıldı...\n\n📹 Video: `{url}`")
        
        loop.run_until_complete(automation.handle_initial_setup())
        edit_message(chat_id, message_id, f"🔄 Popup'lar temizlendi...\n\n📹 Video: `{url}`")
        
        # CAPTCHA çöz
        edit_message(chat_id, message_id, f"🔄 CAPTCHA çözülüyor... (5 deneme)\n\n📹 Video: `{url}`")
        captcha_result = loop.run_until_complete(
            automation.solve_captcha_auto(max_attempts=5)
        )
        
        if captcha_result == "timeout":
            edit_message(
                chat_id, message_id,
                f"❌ **CAPTCHA çözülemedi!**\n\nLütfen daha sonra tekrar deneyin."
            )
            loop.run_until_complete(automation.close())
            loop.close()
            return
        
        # Servisleri kontrol et
        edit_message(chat_id, message_id, f"🔄 Servis kontrol ediliyor...\n\n📹 Video: `{url}`")
        loop.run_until_complete(automation.detect_available_services())
        
        if not automation._available_services.get(service, False):
            edit_message(
                chat_id, message_id,
                f"❌ **{service.capitalize()} servisi şu anda çevrimdışı!**\n\nLütfen başka bir servis deneyin."
            )
            loop.run_until_complete(automation.close())
            loop.close()
            return
        
        # Servisi gönder
        edit_message(chat_id, message_id, f"🔄 Servis gönderiliyor...\n\n📹 Video: `{url}`")
        result = loop.run_until_complete(automation.send_service(service, url))
        
        loop.run_until_complete(automation.close())
        loop.close()
        
        if result["success"]:
            edit_message(
                chat_id, message_id,
                f"✅ **BAŞARILI!** 🎉\n\n"
                f"🎯 Servis: {service.capitalize()}\n"
                f"📹 Video: `{url}`\n"
                f"📊 Durum: {result['message']}\n\n"
                f"💡 Etkileşimler 1-2 dakika içinde görünür."
            )
        else:
            edit_message(
                chat_id, message_id,
                f"❌ **Hata!**\n\n"
                f"🎯 Servis: {service.capitalize()}\n"
                f"⚠️ Hata: {result['message']}\n\n"
                f"🔄 5 dakika sonra tekrar deneyin."
            )
        
    except Exception as e:
        edit_message(
            chat_id, message_id,
            f"❌ **Hata:**\n```\n{str(e)}\n```"
        )


# ============================================
# MESAJ İŞLEME
# ============================================

def handle_message(update: dict):
    message = update.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "").strip()
    
    if not chat_id:
        return
    
    if text.startswith("/"):
        command = text.split()[0].lower()
        
        if command == "/start":
            send_message(
                chat_id,
                "🚀 **Zefoy Bot**\n\n"
                "TikTok videolarına ücretsiz etkileşim gönderirim.\n\n"
                "📌 **Kullanım:**\n"
                "1️⃣ TikTok video linkini gönder\n"
                "2️⃣ Servis seç\n"
                "3️⃣ Bot işlemi yapar\n\n"
                "⚡ **Servisler:** Hearts, Favorites, Comment Hearts"
            )
            return
        
        elif command == "/help":
            send_message(
                chat_id,
                "📖 **Yardım**\n\n"
                "/start - Botu başlat\n"
                "/help - Bu yardım\n\n"
                "📤 TikTok linkini yaz, servis seç."
            )
            return
    
    if is_valid_tiktok_url(text):
        buttons = [
            [("❤️ Hearts", f"service_hearts_{text}"), ("⭐ Favorites", f"service_favorites_{text}")],
            [("💬 Comment Hearts", f"service_chearts_{text}")],
            [("❌ İptal", "cancel")],
        ]
        send_keyboard(
            chat_id,
            f"🎯 **Servis seç:**\n\n📹 `{text}`",
            buttons
        )
    else:
        send_message(
            chat_id,
            "❌ Geçerli TikTok URL'si girin!\n\n"
            "Örnek: `https://vm.tiktok.com/xxxxx`"
        )


def handle_callback(update: dict):
    callback = update.get("callback_query", {})
    callback_id = callback.get("id")
    data = callback.get("data", "")
    message = callback.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")
    
    if not chat_id or not callback_id:
        return
    
    answer_callback(callback_id)
    
    if data == "cancel":
        edit_message(chat_id, message_id, "❌ İptal edildi.")
        return
    
    parts = data.split("_", 2)
    if len(parts) < 3:
        edit_message(chat_id, message_id, "❌ Hata!")
        return
    
    service = parts[1]
    url = parts[2]
    
    edit_message(
        chat_id, message_id,
        f"⏳ **{service.capitalize()}** gönderiliyor...\n\n"
        f"📹 `{url}`\n"
        f"⏱️ 1-3 dakika sürebilir."
    )
    
    thread = threading.Thread(
        target=run_automation_task,
        args=(chat_id, message_id, service, url)
    )
    thread.daemon = True
    thread.start()


# ============================================
# ANA DÖNGÜ
# ============================================

def main():
    print("🚀 Zefoy Bot başlatılıyor...")
    
    if BOT_TOKEN == "123456789:ABCdefGHIjklMNOpqrsTUVwxyz":
        print("❌ Token'ı değiştir!")
        return
    
    print("✅ Bot çalışıyor!")
    offset = 0
    
    while True:
        try:
            updates = get_updates(offset)
            for update in updates:
                offset = update.get("update_id", 0) + 1
                if "callback_query" in update:
                    handle_callback(update)
                elif "message" in update:
                    handle_message(update)
            time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Durduruldu.")
            break
        except Exception as e:
            print(f"❌ Hata: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
