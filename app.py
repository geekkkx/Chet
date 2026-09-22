import asyncio
import aiohttp
import string
import random

# Base URL for Perchance
BASE_URL = "https://perchance.org/"
# Allowed characters for the random slug
CHARSET = string.ascii_lowercase + string.digits
# Random slug length
SLUG_LENGTH = 10
# Maximum concurrent requests
CONCURRENCY_LIMIT = 100

# User-Agent list to reduce blocking from servers
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
]


async def check_url(session, slug, semaphore):
    url = f"{BASE_URL}{slug}"
    headers = {"User-Agent": random.choice(USER_AGENTS)}

    async with semaphore:
        try:
            timeout = aiohttp.ClientTimeout(total=2)
            async with session.head(url, headers=headers, timeout=timeout) as response:
                if response.status == 200:
                    print(f"[!] Found Private Generator: {url}")
                    with open("private_gens_found.txt", "a", encoding="utf-8") as f:
                        f.write(url + "\n")
                    return True
        except (aiohttp.ClientError, asyncio.TimeoutError):
            pass

    return False


async def main():
    print(f"Starting High-Speed Async Scan... Target Length: {SLUG_LENGTH}")
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

    async with aiohttp.ClientSession() as session:
        while True:
            tasks = []
            for _ in range(CONCURRENCY_LIMIT):
                random_slug = "".join(random.choices(CHARSET, k=SLUG_LENGTH))
                tasks.append(check_url(session, random_slug, semaphore))

            await asyncio.gather(*tasks)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nScan stopped by user.")
