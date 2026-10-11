#!/usr/bin/env python3
"""Fetch Musk-company headlines from Google News RSS and merge them into data/news.json.

Standard library only, so it runs on a stock GitHub Actions runner.
Stores headlines, source names and links only (no article text).

Env vars (all optional):
  NTFY_TOPIC   ntfy.sh topic to push "major" headlines to your phone
  NTFY_SERVER  defaults to https://ntfy.sh
  NEWS_FILE    defaults to data/news.json
  FIXTURE_DIR  read <company>.xml from this folder instead of the network (for testing)
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

NEWS_FILE = os.environ.get("NEWS_FILE", "data/news.json")
MAX_ITEMS = 500
MAX_AGE_DAYS = 45
LOOKBACK = "2d"

# One Google News search per company. Edit these to tune what you follow.
FEEDS = {
    "tesla": '"Tesla" (Musk OR Cybercab OR robotaxi OR Optimus OR FSD OR deliveries OR TSLA OR Gigafactory)',
    "spacex": '"SpaceX" (Starship OR Falcon OR launch OR SPCX OR earnings OR Dragon) -Starlink',
    "starlink": '"Starlink"',
    "neuralink": '"Neuralink"',
    "terafab": '"Terafab"',
    "ai": '(xAI OR SpaceXAI OR Grok OR Grokipedia OR "X Corp") Musk',
    "boring": '"Boring Company" OR "Vegas Loop"',
    "musk": '"Elon Musk" -Tesla -SpaceX -Starlink -Neuralink',
}

MAJOR = re.compile(
    r"\b(deliveries|earnings|quarterly results|recall(s|ed|ing)?|NHTSA|FDA|approval|approved|"
    r"acquir\w*|acquisition|merger|IPO|lawsuit|sues|sued|verdict|ruling|SEC|investigation|probe|"
    r"explod\w*|explosion|anomaly|failure|crash\w*|outage|record|first[- ]ever|unveil\w*|launch(es|ed)? of|"
    r"layoffs?|resign\w*|steps down|guidance|ban(s|ned)?|billion|trillion|pay package|"
    r"orbit(al)? (flight|test)|catch(es)?|splashdown|implant(ed)?)\b",
    re.I,
)
MINOR = re.compile(r"\b(price target|stock (rises|falls|slips|climbs)|should you buy|prediction|opinion|here's why|vs\.?)\b", re.I)
JUNK = re.compile(r"\b(horoscope|lottery|casino|giveaway|crypto airdrop)\b", re.I)


def now_utc():
    return datetime.now(timezone.utc)


def feed_url(query):
    q = urllib.parse.quote(f"{query} when:{LOOKBACK}")
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


def get_xml(company, query):
    fixture = os.environ.get("FIXTURE_DIR")
    if fixture:
        path = os.path.join(fixture, f"{company}.xml")
        if not os.path.exists(path):
            return None
        with open(path, "rb") as f:
            return f.read()
    req = urllib.request.Request(feed_url(query), headers={"User-Agent": "Mozilla/5.0 (MuskWire RSS reader)"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.read()
    except Exception as e:  # one bad feed shouldn't stop the others
        print(f"[{company}] fetch failed: {e}", file=sys.stderr)
        return None


def norm(title):
    t = re.sub(r"[^a-z0-9 ]+", " ", title.lower())
    words = [w for w in t.split() if len(w) > 2]
    return set(words)


def similar(a, b):
    if not a or not b:
        return False
    return len(a & b) / min(len(a), len(b)) >= 0.7


def slug(text, date):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60].strip("-")
    return f"{s}-{date[:10]}"


def classify(title):
    if MINOR.search(title):
        return "minor"
    if MAJOR.search(title):
        return "major"
    return "notable"


def parse_feed(company, raw):
    out = []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        print(f"[{company}] bad XML: {e}", file=sys.stderr)
        return out
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        src_el = it.find("source")
        source = (src_el.text or "").strip() if src_el is not None and src_el.text else ""
        if source and title.endswith(" - " + source):
            title = title[: -(len(source) + 3)].strip()
        if not title or not link.startswith("http") or JUNK.search(title):
            continue
        try:
            pub = parsedate_to_datetime(it.findtext("pubDate") or "").astimezone(timezone.utc)
        except Exception:
            pub = now_utc()
        out.append({
            "company": company,
            "title": title,
            "url": link,
            "source": source or "Google News",
            "publishedAt": pub.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "importance": classify(title),
        })
    return out


def load():
    try:
        with open(NEWS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"items": [], "events": []}


def notify(new_major):
    topic = os.environ.get("NTFY_TOPIC", "").strip()
    if not topic or not new_major:
        return
    server = os.environ.get("NTFY_SERVER", "https://ntfy.sh").rstrip("/")
    names = {"tesla": "Tesla", "spacex": "SpaceX", "starlink": "Starlink", "neuralink": "Neuralink",
             "terafab": "Terafab", "ai": "xAI/X", "boring": "Boring Co", "musk": "Musk"}
    for item in new_major[:5]:  # cap per run so a busy news day doesn't spam you
        body = item["title"].encode("utf-8")
        req = urllib.request.Request(f"{server}/{urllib.parse.quote(topic)}", data=body, method="POST")
        req.add_header("Title", f"Musk Wire: {names.get(item['company'], 'News')}")
        req.add_header("Click", item["url"])
        req.add_header("Tags", "rotating_light")
        try:
            urllib.request.urlopen(req, timeout=15).read()
        except Exception as e:
            print(f"ntfy failed: {e}", file=sys.stderr)


def main():
    data = load()
    items = data.get("items", [])
    seen_urls = {i["url"] for i in items}
    seen_titles = [norm(i["title"]) for i in items]
    stamp = now_utc().strftime("%Y-%m-%dT%H:%M:%SZ")

    added = []
    for company, query in FEEDS.items():
        raw = get_xml(company, query)
        if not raw:
            continue
        for it in parse_feed(company, raw):
            n = norm(it["title"])
            if it["url"] in seen_urls or any(similar(n, s) for s in seen_titles):
                continue
            it["id"] = slug(it["title"], it["publishedAt"])
            it["addedAt"] = stamp
            items.append(it)
            added.append(it)
            seen_urls.add(it["url"])
            seen_titles.append(n)

    cutoff = now_utc() - timedelta(days=MAX_AGE_DAYS)
    def ts(i):
        try:
            d = datetime.fromisoformat(i["publishedAt"].replace("Z", "+00:00"))
            return d if d.tzinfo else d.replace(hour=12, tzinfo=timezone.utc)
        except Exception:
            return now_utc()
    items = [i for i in items if ts(i) >= cutoff or i.get("pinned")]
    items.sort(key=ts, reverse=True)
    items = items[:MAX_ITEMS]

    today = now_utc().date().isoformat()
    events = [e for e in data.get("events", []) if e.get("date", "") >= today]

    data = {"updatedAt": stamp, "items": items, "events": events}
    os.makedirs(os.path.dirname(NEWS_FILE) or ".", exist_ok=True)
    with open(NEWS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    major = [i for i in added if i["importance"] == "major"]
    print(f"Added {len(added)} items ({len(major)} major). Total {len(items)}.")
    notify(major)


if __name__ == "__main__":
    main()
