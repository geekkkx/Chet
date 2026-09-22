import argparse
import asyncio
import random
import string
from pathlib import Path

import aiohttp

BASE_URL = "https://perchance.org/"
CHARSET = string.ascii_lowercase + string.digits
DEFAULT_SLUG_LENGTH = 10
DEFAULT_CONCURRENCY = 50
DEFAULT_MAX_HITS = 10
DEFAULT_RETRIES = 3
REQUEST_TIMEOUT = 2.0

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
]


def random_slug(length: int) -> str:
    return "".join(random.choices(CHARSET, k=length))


async def check_url(session: aiohttp.ClientSession, slug: str, semaphore: asyncio.Semaphore, output_file: Path) -> bool:
    url = f"{BASE_URL}{slug}"
    headers = {"User-Agent": random.choice(USER_AGENTS)}

    for attempt in range(1, DEFAULT_RETRIES + 1):
        async with semaphore:
            try:
                timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
                async with session.head(url, headers=headers, timeout=timeout, allow_redirects=True) as response:
                    if response.status == 200:
                        print(f"[!] Found Private Generator: {url}")
                        with output_file.open("a", encoding="utf-8") as f:
                            f.write(url + "\n")
                        return True

                    if response.status in {403, 429}:
                        await asyncio.sleep(random.uniform(0.25, 0.75))
                        continue

            except (aiohttp.ClientError, asyncio.TimeoutError):
                pass

            except Exception:
                pass

        await asyncio.sleep(random.uniform(0.05, 0.2))

    return False


async def scan(args):
    output_file = Path(args.output)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    semaphore = asyncio.Semaphore(args.concurrency)
    hit_count = 0
    total_attempts = 0

    async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(limit=args.concurrency * 2),
        trust_env=True,
    ) as session:
        while hit_count < args.max_hits:
            tasks = []
            for _ in range(args.concurrency):
                slug = random_slug(args.slug_length)
                tasks.append(check_url(session, slug, semaphore, output_file))

            batch_results = await asyncio.gather(*tasks)
            found_in_batch = sum(batch_results)
            hit_count += found_in_batch
            total_attempts += len(batch_results)

            print(
                f"Batch done: found={hit_count}, attempted={total_attempts}, concurrency={args.concurrency}",
                flush=True,
            )

            if found_in_batch and hit_count >= args.max_hits:
                print(f"Reached target hit limit ({args.max_hits}). Stopping.")
                break

            if args.delay > 0:
                await asyncio.sleep(random.uniform(args.delay * 0.5, args.delay * 1.5))


def parse_args():
    parser = argparse.ArgumentParser(description="Scan for private Perchance generator URLs.")
    parser.add_argument("--slug-length", type=int, default=DEFAULT_SLUG_LENGTH, help="Length of the random URL slug to generate.")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY, help="Number of tasks to run in parallel.")
    parser.add_argument("--max-hits", type=int, default=DEFAULT_MAX_HITS, help="Stop after this many matches are found.")
    parser.add_argument("--delay", type=float, default=0.25, help="Delay between batches in seconds.")
    parser.add_argument("--output", type=str, default="private_gens_found.txt", help="File to write found URLs to.")
    return parser.parse_args()


async def main():
    args = parse_args()
    print(
        f"Starting async scan | slug_length={args.slug_length} concurrency={args.concurrency} max_hits={args.max_hits}")
    await scan(args)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nScan stopped by user.")
