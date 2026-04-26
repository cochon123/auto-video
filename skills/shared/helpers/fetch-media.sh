#!/usr/bin/env python3
"""Fetch media assets from various sources (Pexels, DuckDuckGo, Pixabay, local)."""

import argparse
import json
import shutil
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

DELAY_BETWEEN_REQUESTS = 5.0


def _load_config(config_path: str | None) -> dict:
    if not config_path:
        return {}
    try:
        import yaml
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        print("PyYAML required for --config. pip install pyyaml", file=sys.stderr)
    except FileNotFoundError:
        print(f"Config not found: {config_path}", file=sys.stderr)
    return {}


def _get_pexels_key(config: dict) -> str:
    media = config.get("media", {})
    providers = media.get("providers", [])
    if isinstance(providers, list):
        for p in providers:
            if isinstance(p, dict) and p.get("name") == "pexels":
                return p.get("api_key", "")
    if isinstance(providers, dict):
        return providers.get("pexels_api_key", "")
    return media.get("pexels_api_key", "")


def _get_pixabay_key(config: dict) -> str:
    media = config.get("media", {})
    providers = media.get("providers", [])
    if isinstance(providers, list):
        for p in providers:
            if isinstance(p, dict) and p.get("name") == "pixabay":
                return p.get("api_key", "")
    return media.get("pixabay_api_key", "")


def fetch_pexels(query: str, api_key: str, media_type: str = "image", count: int = 3) -> list[dict]:
    if media_type == "video":
        url = f"https://api.pexels.com/videos/search?query={urllib.parse.quote(query)}&per_page={count}"
    else:
        url = f"https://api.pexels.com/v1/search?query={urllib.parse.quote(query)}&per_page={count}"
    req = urllib.request.Request(url, headers={"Authorization": api_key, "User-Agent": "auto-video/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        print(f"[pexels] Error fetching '{query}': {exc}", file=sys.stderr)
        return []

    results = []
    items = data.get("photos", []) if media_type == "image" else data.get("videos", [])
    for item in items[:count]:
        if media_type == "image":
            src = item.get("src", {}).get("large", item.get("src", {}).get("original", ""))
        else:
            files = item.get("video_files", [])
            hd = [f for f in files if f.get("quality") == "hd"]
            src = (hd[0] if hd else (files[0] if files else {})).get("link", "")
        if src:
            results.append({"url": src, "source": "pexels", "query": query})
    return results


def fetch_duckduckgo(query: str, count: int = 5) -> list[dict]:
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            print("[duckduckgo] Install ddgs: pip install ddgs", file=sys.stderr)
            return []
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.images(query, max_results=count):
                results.append({"url": r.get("image", ""), "source": "duckduckgo", "query": query})
    except Exception as exc:
        print(f"[duckduckgo] Error fetching '{query}': {exc}", file=sys.stderr)
    return results


def fetch_pixabay(query: str, api_key: str, media_type: str = "image", count: int = 3) -> list[dict]:
    endpoint = "videos/" if media_type == "video" else ""
    base = f"https://pixabay.com/api/{endpoint}?"
    params = urllib.parse.urlencode({"key": api_key, "q": query, "per_page": count, "image_type": "photo"})
    url = base + params
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read())
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        print(f"[pixabay] Error fetching '{query}': {exc}", file=sys.stderr)
        return []
    results = []
    hits = data.get("hits", [])
    for item in hits[:count]:
        src = item.get("largeImageURL", item.get("webformatURL", ""))
        if media_type == "video":
            vids = item.get("videos", {})
            hd = vids.get("large", vids.get("medium", vids.get("small", {})))
            src = hd.get("url", "")
        if src:
            results.append({"url": src, "source": "pixabay", "query": query})
    return results


def fetch_local(query: str, local_path: str, count: int = 3) -> list[dict]:
    p = Path(local_path)
    if not p.exists():
        print(f"[local] Path does not exist: {local_path}", file=sys.stderr)
        return []
    extensions = {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".avi"}
    query_lower = query.lower()
    matches = []
    for f in p.rglob("*"):
        if f.suffix.lower() in extensions:
            if query_lower in f.name.lower() or query_lower in f.stem.lower():
                matches.append({"url": str(f), "source": "local", "query": query})
    return matches[:count]


def download_file(url: str, output_dir: Path, prefix: str = "asset") -> str | None:
    if url.startswith("/"):
        src = Path(url)
        if src.exists():
            ext = src.suffix
            dest = output_dir / f"{prefix}{ext}"
            shutil.copy2(src, dest)
            return str(dest)
        return None
    ext = ".jpg"
    if ".mp4" in url or ".mov" in url:
        ext = ".mp4"
    elif ".png" in url:
        ext = ".png"
    elif ".webp" in url:
        ext = ".webp"
    dest = output_dir / f"{prefix}{ext}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "auto-video/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            dest.write_bytes(resp.read())
        return str(dest)
    except Exception as exc:
        print(f"[download] Failed {url}: {exc}", file=sys.stderr)
        return None


def fetch_batch(
    queries: list[str],
    source: str,
    output_dir: Path,
    config: dict,
    media_type: str = "image",
    count: int = 2,
    delay: float = DELAY_BETWEEN_REQUESTS,
) -> list[dict]:
    """Fetch multiple queries with delay between requests to avoid rate limits."""
    all_downloaded = []
    for i, query in enumerate(queries):
        if i > 0 and delay > 0:
            print(f"  Waiting {delay:.0f}s before next request...")
            time.sleep(delay)

        print(f"  [{i+1}/{len(queries)}] Fetching '{query}' from {source}...")
        results = []

        if source == "pexels":
            key = _get_pexels_key(config)
            if key:
                results = fetch_pexels(query, key, media_type, count)
            else:
                print(f"    No Pexels API key, falling back to duckduckgo", file=sys.stderr)
                results = fetch_duckduckgo(query, count)
        elif source == "duckduckgo":
            results = fetch_duckduckgo(query, count)
        elif source == "pixabay":
            key = _get_pixabay_key(config)
            if key:
                results = fetch_pixabay(query, key, media_type, count)
            else:
                results = fetch_duckduckgo(query, count)
        elif source == "local":
            lpath = config.get("media", {}).get("local_path", ".")
            results = fetch_local(query, lpath, count)

        if not results and source != "duckduckgo":
            print(f"    {source} returned nothing, trying duckduckgo fallback...")
            results = fetch_duckduckgo(query, count)

        safe_query = query.replace(" ", "_")[:30]
        for j, item in enumerate(results[:count]):
            path = download_file(item["url"], output_dir, prefix=f"{safe_query}_{j}")
            if path:
                all_downloaded.append({"path": path, **item})

    return all_downloaded


def main():
    parser = argparse.ArgumentParser(description="Fetch media assets from various sources")
    parser.add_argument("--query", default=None, help="Single search query")
    parser.add_argument("--queries-file", default=None, help="JSON file with list of {query, source, type} objects")
    parser.add_argument("--source", default="duckduckgo", choices=["pexels", "duckduckgo", "pixabay", "local", "auto"])
    parser.add_argument("--type", default="image", choices=["image", "video"])
    parser.add_argument("--output-dir", default=".", help="Directory to save downloaded assets")
    parser.add_argument("--count", type=int, default=2, help="Max items per query")
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--local-path", default=None)
    parser.add_argument("--config", default="~/.config/auto-video/config.yaml")
    parser.add_argument("--delay", type=float, default=DELAY_BETWEEN_REQUESTS, help="Delay between requests in seconds")
    parser.add_argument("--test", metavar="PROVIDER", help="Test a specific provider")
    parser.add_argument("--test-all", action="store_true", help="Test all configured providers")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()

    config_path = args.config.replace("~", str(Path.home())) if args.config else None
    config = _load_config(config_path)

    if args.test:
        source = args.test
        print(f"Testing {source}...")
        if source == "pexels":
            key = args.api_key or _get_pexels_key(config)
            if not key:
                print("ERROR: Pexels API key required", file=sys.stderr)
                sys.exit(1)
            results = fetch_pexels("nature", key, count=1)
        elif source == "duckduckgo":
            results = fetch_duckduckgo("nature", count=1)
        elif source == "pixabay":
            key = args.api_key or _get_pixabay_key(config)
            if not key:
                print("ERROR: Pixabay API key required", file=sys.stderr)
                sys.exit(1)
            results = fetch_pixabay("nature", key, count=1)
        else:
            results = []
        print(f"{'OK' if results else 'FAIL'}: {source} returned {len(results)} result(s)")
        sys.exit(0 if results else 1)

    if args.test_all:
        media_cfg = config.get("media", {})
        providers = media_cfg.get("providers", [])
        all_ok = True
        for prov in providers:
            name = prov.get("name", "") if isinstance(prov, dict) else str(prov)
            print(f"Testing {name}...", end=" ", flush=True)
            if name == "pexels":
                key = prov.get("api_key", "") if isinstance(prov, dict) else ""
                ok = bool(fetch_pexels("test", key, count=1))
            elif name == "duckduckgo":
                ok = bool(fetch_duckduckgo("test", count=1))
            elif name == "pixabay":
                key = prov.get("api_key", "") if isinstance(prov, dict) else ""
                ok = bool(fetch_pixabay("test", key, count=1))
            else:
                ok = True
            print("OK" if ok else "FAIL")
            if not ok:
                all_ok = False
        sys.exit(0 if all_ok else 1)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.queries_file:
        with open(args.queries_file) as f:
            queries_data = json.load(f)
        if isinstance(queries_data, list):
            query_strings = []
            sources_map = {}
            for item in queries_data:
                q = item.get("query", "") if isinstance(item, dict) else str(item)
                if q:
                    query_strings.append(q)
                    sources_map[q] = item.get("source", args.source) if isinstance(item, dict) else args.source
            source = args.source
            downloaded = fetch_batch(query_strings, source, output_dir, config, args.type, args.count, args.delay)
        else:
            downloaded = []
    elif args.query:
        downloaded = fetch_batch([args.query], args.source, output_dir, config, args.type, args.count, delay=0)
    else:
        parser.print_help()
        return

    if args.json:
        print(json.dumps(downloaded, indent=2))
    else:
        for d in downloaded:
            print(d["path"])
        print(f"\nTotal: {len(downloaded)} assets downloaded")


if __name__ == "__main__":
    main()
