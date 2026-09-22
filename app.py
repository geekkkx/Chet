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
DEFAULT_DELAY = 0.25
DEFAULT_RETRIES = 3
REQUEST_TIMEOUT_SECONDS = 2.0

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
]


def random_slug(length: int) -> str:
    if length <= 0:
        raise ValueError("slug_length must be greater than 0")
    return "".join(random.choices(CHARSET, k=length))


async def check_url(
    session: aiohttp.ClientSession,
    slug: str,
    semaphore: asyncio.Semaphore,
    output_file: Path,
    retries: int,
    request_timeout: float,
) -> bool:
    url = f"{BASE_URL}{slug}"
    headers = {"User-Agent": random.choice(USER_AGENTS)}

    for attempt in range(1, retries + 1):
        async with semaphore:
            try:
                timeout = aiohttp.ClientTimeout(total=request_timeout)
                async with session.head(
                    url,
                    headers=headers,
                    timeout=timeout,
                    allow_redirects=True,
                ) as response:
                    if response.status == 200:
                        print(f"[!] Found Private Generator: {url}")
                        with output_file.open("a", encoding="utf-8") as file_handle:
                            file_handle.write(url + "\n")
                        return True

                    if response.status in {403, 429}:
                        await asyncio.sleep(random.uniform(0.25, 0.75))
                        continue

            except (aiohttp.ClientError, asyncio.TimeoutError):
                pass

        await asyncio.sleep(random.uniform(0.05, 0.2))

    return False


async def scan(args):
    if args.max_hits <= 0:
        print("max_hits must be greater than 0")
        return

    if args.slug_length <= 0:
        print("slug_length must be greater than 0")
        return

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
            batch_size = min(args.concurrency, args.max_hits - hit_count)
            tasks = []

            for _ in range(batch_size):
                slug = random_slug(args.slug_length)
                tasks.append(
                    check_url(
                        session=session,
                        slug=slug,
                        semaphore=semaphore,
                        output_file=output_file,
                        retries=args.retries,
                        request_timeout=args.request_timeout,
                    )
                )

            batch_results = await asyncio.gather(*tasks)
            batch_hits = sum(batch_results)
            hit_count += batch_hits
            total_attempts += len(batch_results)

            print(
                f"Batch complete: found={hit_count}, attempted={total_attempts}, concurrency={args.concurrency}",
                flush=True,
            )

            if hit_count >= args.max_hits:
                print(f"Target reached: {args.max_hits} hits found. Stopping.")
                break

            if args.delay > 0:
                await asyncio.sleep(random.uniform(args.delay * 0.5, args.delay * 1.5))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="High-speed async scanner for private Perchance generator URLs."
    )
    parser.add_argument(
        "--slug-length",
        type=int,
        default=DEFAULT_SLUG_LENGTH,
        help="Length of the generated URL slug.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=DEFAULT_CONCURRENCY,
        help="Maximum number of concurrent requests.",
    )
    parser.add_argument(
        "--max-hits",
        type=int,
        default=DEFAULT_MAX_HITS,
        help="Stop after discovering this many valid matches.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY,
        help="Delay between request batches in seconds.",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help="Number of retries per URL before giving up.",
    )
    parser.add_argument(
        "--request-timeout",
        type=float,
        default=REQUEST_TIMEOUT_SECONDS,
        help="Per-request timeout in seconds.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="private_gens_found.txt",
        help="File path to write found URLs to.",
    )
    return parser.parse_args()


async def main():
    args = parse_args()
    print(
        f"Starting async scan | slug_length={args.slug_length} "
        f"concurrency={args.concurrency} max_hits={args.max_hits}"
    )
    await scan(args)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nScan stopped by user.")
