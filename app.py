import asyncio
import aiohttp
import string
import random

# ပစ်မှတ် Base URL
BASE_URL = "https://perchance.org/"
# အသုံးပြုမည့် စာလုံးများ (အင်္ဂလိပ်စာလုံး အသေးနှင့် ဂဏန်းများ)
CHARSET = string.ascii_lowercase + string.digits
# ရှာဖွေမည့် String အရှည် (Perchance random URL အရှည်ကို အခြေခံ၍ သတ်မှတ်ရန်)
SLUG_LENGTH = 10 
# တစ်ကြိမ်တည်း ပို့မည့် request အရေအတွက်
CONCURRENCY_LIMIT = 100

# User-Agent များ စုစည်းမှု (Server မှ ပိတ်ဆို့မှုကို ရှောင်ရန်)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
]

async def check_url(session, slug):
    url = f"{BASE_URL}{slug}"
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    try:
        # HEAD request သုံး၍ စာမျက်နှာ ရှိမရှိ မြန်မြန်စစ်ဆေးခြင်း
        async with session.head(url, headers=headers, timeout=2) as response:
            if response.status == 200:
                print(f"[!] Found Private Generator: {url}")
                with open("private_gens_found.txt", "a") as f:
                    f.write(url + "\n")
                return True
    except:
        pass
    return False

async def main():
    print(f"Starting High-Speed Async Scan... Target Length: {SLUG_LENGTH}")
    # Semaphore သုံး၍ တစ်ပြိုင်တည်း ပို့မည့် request အရေအတွက်ကို ကန့်သတ်ခြင်း
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    
    async with aiohttp.ClientSession() as session:
        while True:
            tasks = []
            for _ in range(CONCURRENCY_LIMIT):
                # Random string များကို ဖန်တီးခြင်း
                random_slug = ''.join(random.choices(CHARSET, k=SLUG_LENGTH))
                tasks.append(check_url(session, random_slug))
            
            # Task အားလုံးကို ပြိုင်တူ လုပ်ဆောင်စေခြင်း
            await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nScan stopped by user.")
