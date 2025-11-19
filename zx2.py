#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import csv
import time
import math
import glob
import random
from typing import List, Dict, Optional, Tuple

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import http.client
import json
import requests
import argparse
import hashlib

START_URL = "https://zxcard.yimieji.com/search#1758533406932.175"
OUTPUT_CSV = "zx2_cards.csv"
DEBUG_DIR = "debug_yimieji"
DETAIL_DIR = os.path.join(DEBUG_DIR, "details")
FULL_OUTPUT_CSV = "zx2_cards_full.csv"
STATE_FILE = os.path.join(DEBUG_DIR, "detail_state.json")

# Selenium timeouts
PAGE_LOAD_TIMEOUT_SEC = 30
IMPLICIT_WAIT_SEC = 5
EXPLICIT_WAIT_SEC = 20

REQUEST_TIMEOUT = 20

USER_AGENTS = [
    # Common desktop Chrome UAs
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


def jitter_sleep(base: float = 1.0, spread: float = 0.6) -> None:
    time.sleep(max(0.2, random.uniform(base - spread, base + spread)))


def ensure_dirs() -> None:
    if not os.path.isdir(DEBUG_DIR):
        os.makedirs(DEBUG_DIR, exist_ok=True)


def create_driver(headless: bool = True) -> webdriver.Chrome:
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--lang=zh-CN,zh;q=0.9,en;q=0.8")
    chrome_options.add_argument(f"--user-agent={random.choice(USER_AGENTS)}")

    # Reduce background network activity and disable push/notifications
    chrome_options.add_argument("--disable-background-networking")
    chrome_options.add_argument("--disable-sync")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-default-apps")
    chrome_options.add_argument("--metrics-recording-only")
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--disable-features=PushMessaging,Notifications,TranslateUI,OptimizationHints,AutoupgradeMixedContent,BackgroundFetch")
    chrome_options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.notifications": 2,
        "profile.default_content_setting_values.geolocation": 2,
        "profile.managed_default_content_settings.images": 1,
        "autofill.profile_enabled": False,
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
    })

    # Prefer Selenium Manager to avoid proxy issues
    try:
        driver = webdriver.Chrome(options=chrome_options)
    except Exception:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT_SEC)
    driver.implicitly_wait(IMPLICIT_WAIT_SEC)
    return driver


def get_last_saved_page_index() -> int:
    ensure_dirs()
    files = glob.glob(os.path.join(DEBUG_DIR, "yimieji_page_*.html"))
    if not files:
        return 0
    idxs = []
    for p in files:
        m = re.search(r"(\d+)", p)
        if m:
            idxs.append(int(m.group(1)))
    return max(idxs) if idxs else 0


def write_csv_header(path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "card_id",
                "card_number",
                "name",
                "rarity",
                "type",
                "race",
                "cost",
                "power",
                "life",
                "illustrator",
                "text",
                "image_url",
                "detail_url",
            ],
        )
        writer.writeheader()


def append_rows(path: str, rows: List[Dict[str, str]]) -> None:
    if not rows:
        return
    with open(path, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "card_id","card_number","name","rarity","type","race","cost","power","life","illustrator","text","image_url","detail_url"
        ])
        writer.writerows(rows)


def save_debug_html(page_index: int, html: str) -> str:
    ensure_dirs()
    path = os.path.join(DEBUG_DIR, f"yimieji_page_{page_index}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


def extract_text(el) -> str:
    return el.get_text(strip=True) if el else ""


def parse_cards_from_soup(soup: BeautifulSoup) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []

    # Items often in cards grid; try general selectors
    cards = soup.select(".card, .card-item, .list-item, .ant-card, li")
    if not cards or len(cards) < 10:
        cards = soup.find_all(lambda tag: tag.name in ["div", "li", "article"] and tag.find(string=lambda s: isinstance(s, str) and re.search(r"[A-Z]{1,3}\d{2,}-\d{2,}", s or "")))

    seen_keys = set()

    for node in cards:
        number = ""
        name = ""
        rarity = ""
        ctype = ""
        race = ""
        cost = ""
        power = ""
        life = ""
        illustrator = ""
        text = ""
        image_url = ""
        detail_url = ""
        cid = ""

        # common fields
        number_el = node.select_one(".card-number, .number, .no, .card_no, p.number, span.number")
        name_el = node.select_one(".card-name, .name, h3, h4, .title")
        if number_el:
            number = extract_text(number_el)
        else:
            maybe = node.find(string=lambda s: isinstance(s, str) and re.search(r"[A-Z]{1,3}\d{2,}-\d{2,}", s))
            number = (maybe or "").strip()
        if name_el:
            name = extract_text(name_el)

        a = node.find("a", href=True)
        if a:
            detail_url = a["href"].strip()
            if detail_url.startswith("/"):
                detail_url = "https://zxcard.yimieji.com" + detail_url

        # image
        img = node.find("img")
        if img and img.get("src"):
            image_url = img["src"].strip()
            if image_url.startswith("/"):
                image_url = "https://zxcard.yimieji.com" + image_url

        # labeled attributes in dl
        for dl in node.find_all("dl"):
            for dt in dl.find_all("dt"):
                label = extract_text(dt)
                dd = dt.find_next_sibling("dd")
                val = extract_text(dd)
                if not val:
                    continue
                if any(k in label for k in ["稀有", "稀有度", "RARITY"]):
                    rarity = val
                elif any(k in label for k in ["类型", "卡牌类型", "TYPE"]):
                    ctype = val
                elif any(k in label for k in ["种族", "RACE"]):
                    race = val
                elif any(k in label for k in ["费用", "コスト", "COST"]):
                    cost = val
                elif any(k in label for k in ["力量", "パワー", "POWER"]):
                    power = val
                elif any(k in label for k in ["生命", "ライフ", "LIFE"]):
                    life = val
                elif any(k in label for k in ["画师", "插画", "イラスト", "ILLUSTRATOR"]):
                    illustrator = val

        # text blocks
        text_el = node.select_one(".text, .card-text, .desc, .description, p.text")
        if text_el:
            text = extract_text(text_el)

        # data attrs for id
        for k in ["data-id", "data-card_id", "data-cardid", "data-cid"]:
            if node.has_attr(k):
                cid = str(node.get(k)).strip()
                break

        key = (number, name, detail_url)
        if not number and not name:
            continue
        if key in seen_keys:
            continue
        seen_keys.add(key)

        rows.append({
            "card_id": cid,
            "card_number": number,
            "name": name,
            "rarity": rarity,
            "type": ctype,
            "race": race,
            "cost": cost,
            "power": power,
            "life": life,
            "illustrator": illustrator,
            "text": text,
            "image_url": image_url,
            "detail_url": detail_url,
        })

    return rows


def parse_cards_from_html(html: str) -> List[Dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    return parse_cards_from_soup(soup)


def find_dicts_with_card_like_entries(obj) -> List[Dict[str, any]]:
    found: List[Dict[str, any]] = []
    def walk(x):
        if isinstance(x, dict):
            # heuristic: has number/name-like keys or values
            keys = " ".join(x.keys())
            vals = " ".join([str(v) for v in x.values() if isinstance(v, (str, int))])
            if re.search(r"[A-Z]{1,3}\d{2,}-\d{2,}", vals) or any(k in keys for k in ["cno", "cardNo", "编号", "name", "cname", "jname"]):
                found.append(x)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for it in x:
                walk(it)
    walk(obj)
    return found


def parse_cards_from_nuxt(html: str) -> List[Dict[str, str]]:
    # Extract window.__NUXT__ JSON block
    m = re.search(r"window\.__NUXT__\s*=\s*(\{[\s\S]*?\})\s*;", html)
    if not m:
        return []
    raw = m.group(1)
    # Sanitize: replace undefined with null
    sanitized = re.sub(r"\bundefined\b", "null", raw)
    try:
        data = json.loads(sanitized)
    except Exception:
        return []
    candidates = find_dicts_with_card_like_entries(data)
    rows: List[Dict[str, str]] = []
    seen = set()
    for d in candidates:
        # Map fields heuristically
        number = str(d.get("cno") or d.get("cardNo") or d.get("编号") or "").strip()
        name = str(d.get("cname") or d.get("name") or d.get("中文名") or d.get("title") or "").strip()
        rarity = str(d.get("rarity") or d.get("稀有度") or "").strip()
        ctype = str(d.get("type") or d.get("类型") or "").strip()
        race = str(d.get("race") or d.get("种族") or "").strip()
        cost = str(d.get("cost") or d.get("费用") or "").strip()
        power = str(d.get("power") or d.get("力量") or "").strip()
        life = str(d.get("life") or d.get("生命") or "").strip()
        illustrator = str(d.get("illust") or d.get("illustrator") or d.get("画师") or "").strip()
        text = str(d.get("text") or d.get("能力") or "").strip()
        img = str(d.get("image") or d.get("img") or d.get("image_url") or "").strip()
        url = str(d.get("url") or d.get("link") or "").strip()
        cid = str(d.get("id") or d.get("card_id") or "").strip()
        key = (number, name)
        if not number and not name:
            continue
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            "card_id": cid,
            "card_number": number,
            "name": name,
            "rarity": rarity,
            "type": ctype,
            "race": race,
            "cost": cost,
            "power": power,
            "life": life,
            "illustrator": illustrator,
            "text": text,
            "image_url": img,
            "detail_url": url,
        })
    return rows


def wait_and_trigger_search(driver: webdriver.Chrome) -> None:
    # Click the '搜索' button to populate results
    try:
        buttons = driver.find_elements(By.XPATH, "//button[normalize-space(.)='搜索'] | //a[normalize-space(.)='搜索'] | //*[(self::button or self::a or self::span) and normalize-space(text())='搜索']")
        for btn in buttons:
            if btn.is_displayed() and btn.is_enabled():
                try:
                    btn.click()
                    break
                except WebDriverException:
                    continue
        try:
            WebDriverWait(driver, EXPLICIT_WAIT_SEC).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".ant-pagination, .card, .card-item, .result-item"))
            )
        except TimeoutException:
            pass
    except WebDriverException:
        pass


def auto_scroll(driver: webdriver.Chrome, max_rounds: int = 20) -> None:
    last_height = driver.execute_script("return document.body.scrollHeight")
    rounds = 0
    while rounds < max_rounds:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        jitter_sleep(0.6, 0.4)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
        rounds += 1


def click_next_page(driver: webdriver.Chrome) -> bool:
    # Ant Design pagination next
    selectors = [
        "li.ant-pagination-next:not(.ant-pagination-disabled) button",
        "li.ant-pagination-next:not(.ant-pagination-disabled) a",
        "a[aria-label='Next']", "button[aria-label='Next']",
        "li.next a", "button.next", "a.next",
    ]
    for sel in selectors:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            if el and el.is_enabled():
                el.click()
                return True
        except NoSuchElementException:
            continue
        except WebDriverException:
            continue
    # fallback numbered pages
    try:
        current = driver.find_elements(By.CSS_SELECTOR, "li.ant-pagination-item-active a, li.ant-pagination-item-active")
        next_num = None
        if current:
            try:
                text = current[0].text.strip()
                cur = int(text)
                next_num = str(cur + 1)
            except Exception:
                next_num = None
        if next_num:
            anchors = driver.find_elements(By.XPATH, f"//li[contains(@class,'ant-pagination-item')]/a[normalize-space(text())='{next_num}']")
            for a in anchors:
                if a.is_displayed() and a.is_enabled():
                    a.click()
                    return True
    except WebDriverException:
        pass
    return False


def goto_page(driver: webdriver.Chrome, target_page: int) -> bool:
    try:
        anchors = driver.find_elements(By.XPATH, f"//li[contains(@class,'ant-pagination-item')]/a[normalize-space(text())='{target_page}']")
        for a in anchors:
            if a.is_displayed() and a.is_enabled():
                a.click()
                jitter_sleep(1.2, 0.8)
                return True
    except WebDriverException:
        return False
    return False


def fetch_html_pages(max_pages: Optional[int] = None) -> int:
    ensure_dirs()
    driver = create_driver(headless=True)
    saved = 0
    try:
        driver.get(START_URL)
        try:
            WebDriverWait(driver, EXPLICIT_WAIT_SEC).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except TimeoutException:
            pass

        wait_and_trigger_search(driver)

        start_from = get_last_saved_page_index() + 1
        if start_from > 1:
            goto_page(driver, start_from)

        page_idx = start_from if start_from > 0 else 1
        consecutive_stalls = 0

        while True:
            try:
                auto_scroll(driver, max_rounds=20)
                html = driver.page_source
                save_debug_html(page_idx, html)
                saved += 1
                print(f"Fetched page {page_idx}")

                if max_pages and saved >= max_pages:
                    break

                moved = False
                for attempt in range(3):
                    if click_next_page(driver):
                        moved = True
                        break
                    jitter_sleep(0.8 * (attempt + 1), 0.6)

                if not moved:
                    consecutive_stalls += 1
                    if consecutive_stalls >= 2:
                        break
                    else:
                        try:
                            driver.refresh()
                            jitter_sleep(1.5, 1.0)
                            continue
                        except WebDriverException:
                            break
                else:
                    consecutive_stalls = 0

                jitter_sleep(1.2, 0.8)
                page_idx += 1

            except (ConnectionResetError, http.client.RemoteDisconnected):
                # Network hiccup: recreate driver and resume on current page
                try:
                    driver.quit()
                except Exception:
                    pass
                driver = create_driver(headless=True)
                try:
                    driver.get(START_URL)
                    jitter_sleep(1.0, 0.6)
                    wait_and_trigger_search(driver)
                    goto_page(driver, page_idx)
                    continue
                except Exception:
                    break
            except WebDriverException:
                # Recreate driver once and retry current page
                try:
                    driver.quit()
                except Exception:
                    pass
                driver = create_driver(headless=True)
                try:
                    driver.get(START_URL)
                    jitter_sleep(1.0, 0.6)
                    wait_and_trigger_search(driver)
                    goto_page(driver, page_idx)
                    continue
                except Exception:
                    break
    finally:
        try:
            driver.quit()
        except Exception:
            pass
    return saved


def parse_saved_htmls(max_pages: Optional[int] = None) -> int:
    files = sorted(glob.glob(os.path.join(DEBUG_DIR, "yimieji_page_*.html")), key=lambda p: int(re.search(r"(\d+)", p).group(1)))
    if max_pages:
        files = files[:max_pages]
    write_csv_header(OUTPUT_CSV)

    total = 0
    seen = set()
    for path in files:
        with open(path, "r", encoding="utf-8") as f:
            html = f.read()
        rows = parse_cards_from_html(html)
        if not rows:
            # Fallback via Nuxt state
            rows = parse_cards_from_nuxt(html)
        unique_rows: List[Dict[str, str]] = []
        for r in rows:
            key = (r.get("card_number", ""), r.get("name", ""))
            if key in seen:
                continue
            seen.add(key)
            unique_rows.append(r)
        append_rows(OUTPUT_CSV, unique_rows)
        total += len(unique_rows)
        print(f"Parsed {len(unique_rows)} cards from {os.path.basename(path)} (total {total})")
    return total


def ensure_detail_dir() -> None:
    ensure_dirs()
    if not os.path.isdir(DETAIL_DIR):
        os.makedirs(DETAIL_DIR, exist_ok=True)


def write_full_csv_header(path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "color",
                "card_number",
                "series",
                "rarity",
                "type",
                "jp_name",
                "cn_name",
                "cost",
                "power",
                "race",
                "note",
                "text_full",
                "image_url",
                "detail_url",
            ],
        )
        writer.writeheader()


def append_full_rows(path: str, rows: List[Dict[str, str]]) -> None:
    if not rows:
        return
    with open(path, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "color","card_number","series","rarity","type","jp_name","cn_name","cost","power","race","note","text_full","image_url","detail_url"
        ])
        writer.writerows(rows)


# ---------------------
# Dedupe utilities
# ---------------------
def build_row_key(row: Dict[str, str], strategy: str) -> str:
    s = strategy or "auto"
    if s == "detail_url":
        return (row.get("detail_url", "") or "").strip()
    if s == "image_url":
        return (row.get("image_url", "") or "").strip()
    if s == "card":
        parts = [
            (row.get("card_number", "") or "").strip(),
            (row.get("rarity", "") or "").strip(),
            (row.get("cn_name", "") or "").strip(),
            (row.get("jp_name", "") or "").strip(),
        ]
        return "|".join(parts)
    # auto
    key = (row.get("detail_url", "") or "").strip()
    if key:
        return key
    key = (row.get("image_url", "") or "").strip()
    if key:
        return key
    parts = [
        (row.get("card_number", "") or "").strip(),
        (row.get("rarity", "") or "").strip(),
        (row.get("cn_name", "") or "").strip(),
        (row.get("jp_name", "") or "").strip(),
    ]
    return "|".join(parts)


def dedupe_csv_file(in_path: str, out_path: str, strategy: str = "auto") -> Tuple[int, int]:
    if not os.path.exists(in_path):
        print(f"Input CSV not found: {in_path}")
        return 0, 0
    kept = 0
    total = 0
    seen: set[str] = set()
    with open(in_path, "r", encoding="utf-8") as f_in:
        reader = csv.DictReader(f_in)
        fieldnames = reader.fieldnames or [
            "color","card_number","series","rarity","type","jp_name","cn_name",
            "cost","power","race","note","text_full","image_url","detail_url",
        ]
        with open(out_path, "w", encoding="utf-8", newline="") as f_out:
            writer = csv.DictWriter(f_out, fieldnames=fieldnames)
            writer.writeheader()
            for row in reader:
                total += 1
                key = build_row_key(row, strategy)
                if not key:
                    # fallback to full row hash
                    payload = "\u241F".join([row.get(h, "") for h in fieldnames])
                    key = hashlib.md5(payload.encode("utf-8", errors="ignore")).hexdigest()
                if key in seen:
                    continue
                seen.add(key)
                writer.writerow({h: row.get(h, "") for h in fieldnames})
                kept += 1
    return kept, total


def build_detail_queue_from_list(max_pages: Optional[int] = None) -> List[Dict[str, str]]:
    files = sorted(glob.glob(os.path.join(DEBUG_DIR, "yimieji_page_*.html")), key=lambda p: int(re.search(r"(\d+)", p).group(1)))
    if max_pages:
        files = files[:max_pages]
    queue: List[Dict[str, str]] = []
    seen = set()
    for path in files:
        with open(path, "r", encoding="utf-8") as f:
            html = f.read()
        soup = BeautifulSoup(html, "html.parser")
        items = []
        # Ant List items
        items.extend(soup.select("ul.ant-list-items li.ant-list-item"))
        # Card/item fallbacks
        if not items:
            items.extend(soup.select(".card, .card-item, .list-item"))
        for node in items:
            a = node.find("a", href=True)
            if not a:
                continue
            url = a["href"].strip()
            if url.startswith("/"):
                url = "https://zxcard.yimieji.com" + url
            title = a.get_text(strip=True)
            number = ""
            num_el = node.select_one(".number, .card-number, .no, span.number")
            if num_el:
                number = num_el.get_text(strip=True)
            if not number:
                m = re.search(r"[A-Z]{1,3}\d{2,}-\d{2,}", node.get_text(" ", strip=True))
                number = m.group(0) if m else ""
            key = (url, number)
            if key in seen:
                continue
            seen.add(key)
            queue.append({"detail_url": url, "card_number": number, "title": title})
    return queue


def detail_path_for(url: str, number: str) -> str:
    ensure_detail_dir()
    base = number or re.sub(r"[^a-zA-Z0-9]", "_", url.split("?")[0].rstrip("/").split("/")[-1])
    return os.path.join(DETAIL_DIR, f"{base or 'detail'}.html")


def fetch_detail(driver: webdriver.Chrome, url: str, out_path: str, retries: int = 3) -> bool:
    for i in range(retries):
        try:
            driver.get(url)
            WebDriverWait(driver, EXPLICIT_WAIT_SEC).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            jitter_sleep(0.8, 0.5)
            html = driver.page_source
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(html)
            return True
        except Exception:
            jitter_sleep(1.0 * (i + 1), 0.8)
            continue
    return False


def parse_detail_html(html: str, url: str) -> Dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    text_all = soup.get_text("\n", strip=True)

    # Names (CN/JP)
    jp_name = ""
    cn_name = ""
    # Try prominent title selectors
    title_cn = soup.select_one(".title-cn, .cn, h1, h2")
    title_jp = soup.select_one(".title-jp, .jp")
    if title_cn:
        cn_name = title_cn.get_text(strip=True)
    if title_jp:
        jp_name = title_jp.get_text(strip=True)
    if not cn_name or not jp_name:
        # heuristic split if both languages present in close siblings
        heads = soup.select("h1, h2, .title")
        if heads:
            first = heads[0].get_text(" ", strip=True)
            # leave as fallback to item text below
    
    # Number, color, series, type, rarity
    card_number = ""
    color = ""
    series = ""
    ctype = ""
    rarity = ""

    # Labeled fields via dl/ant-descriptions
    for dt in soup.select("dl dt, .ant-descriptions-item-label"):
        label = dt.get_text(strip=True)
        dd = dt.find_next_sibling("dd") or dt.find_parent().select_one(".ant-descriptions-item-content")
        val = dd.get_text(" ", strip=True) if dd else ""
        if not val:
            continue
        if any(k in label for k in ["编号", "NO", "卡号", "番号"]):
            card_number = val
        elif any(k in label for k in ["颜色", "色", "Color"]):
            color = val
        elif any(k in label for k in ["系列", "收录", "Series"]):
            series = val
        elif any(k in label for k in ["类型", "卡牌类型", "Type"]):
            ctype = val
        elif any(k in label for k in ["稀有", "稀有度", "Rarity"]):
            rarity = val

    if not card_number:
        m = re.search(r"[A-Z]{1,3}\d{2,}-\d{2,}", text_all)
        card_number = m.group(0) if m else ""

    # Stats and race
    cost = ""
    power = ""
    race = ""
    def label_pick(keys: List[str]) -> str:
        for key in keys:
            m = re.search(key + r"\s*[:：]?\s*(\S+)", text_all)
            if m:
                return m.group(1)
        return ""
    cost = label_pick(["费用", "コスト", "Cost"]) or cost
    power = label_pick(["力量", "パワー", "Power"]) or power
    # race value may contain spaces; relax to end of line
    rm = re.search(r"(种族|Race)\s*[:：]?\s*(.+)", text_all)
    race = rm.group(2).strip() if rm else race

    # Notes/Restrictions
    note = ""
    nm = re.search(r"(这张卡不能正规使用。|不能正规使用|注意|备注)[:：]?(.*)", text_all)
    if nm:
        note = nm.group(0)

    # Full ability text: try dedicated blocks
    text_full = ""
    blocks = soup.select(".ability, .text, .desc, .card-text, .ability-text, .cardtext")
    if blocks:
        text_full = "\n".join([b.get_text(" ", strip=True) for b in blocks if b.get_text(strip=True)])
    if not text_full:
        # fallback: slice from first trigger keyword
        km = re.search(r"【[自起常]】[\s\S]+", text_all)
        if km:
            text_full = km.group(0)

    # Image
    img = ""
    img_el = soup.find("img")
    if img_el and img_el.get("src"):
        img = img_el["src"].strip()
        if img.startswith("/"):
            img = "https://zxcard.yimieji.com" + img

    # Names again via heuristics from heading cluster
    if not cn_name or not jp_name:
        heads = soup.select(".title, h1, h2")
        if heads:
            texts = [h.get_text(" ", strip=True) for h in heads if h.get_text(strip=True)]
            if texts:
                # assume first is CN or JP; try to split by script
                for t in texts:
                    if re.search(r"[\u30A0-\u30FF\u3040-\u309F]", t):
                        jp_name = jp_name or t
                    else:
                        cn_name = cn_name or t

    return {
        "color": color,
        "card_number": card_number,
        "series": series,
        "rarity": rarity,
        "type": ctype,
        "jp_name": jp_name,
        "cn_name": cn_name,
        "cost": cost,
        "power": power,
        "race": race,
        "note": note,
        "text_full": text_full,
        "image_url": img,
        "detail_url": url,
    }


def build_requests_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    })
    s.verify = True
    return s


def fetch_detail_requests(session: requests.Session, url: str, out_path: str, retries: int = 4) -> bool:
    for i in range(retries):
        try:
            resp = session.get(url, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200 and resp.text:
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(resp.text)
                return True
        except Exception:
            pass
        jitter_sleep(1.0 * (i + 1), 0.8)
        # rotate UA a bit
        session.headers.update({"User-Agent": random.choice(USER_AGENTS)})
    return False


def parse_list_cards_to_full(html: str) -> List[Dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    rows: List[Dict[str, str]] = []
    # Each card block's right column
    blocks = soup.select("div.ant-col.ant-col-24.ant-col-lg-20")
    for block in blocks:
        try:
            # color, number+rarity, type in head
            head = block.select_one(".meta.head.clearfix")
            color = ""
            card_number = ""
            rarity = ""
            ctype = ""
            if head:
                colorel = head.select_one(".cardColor")
                if colorel:
                    color = colorel.get_text(strip=True)
                head_text = head.get_text(" ", strip=True)
                # e.g., "E53-021 R - Z/X"
                m = re.search(r"([A-Z]{1,3}\d{2,}-\d{2,})\s+([A-Z+]+)", head_text)
                if m:
                    card_number = m.group(1)
                    rarity = m.group(2)
                t = head.select_one("span[style*='float: right']")
                if t:
                    ttxt = t.get_text(" ", strip=True)
                    tm = re.search(r"-\s*(.+)$", ttxt)
                    if tm:
                        ctype = tm.group(1)

            # names
            cn_name = ""
            jp_name = ""
            h2 = block.select_one("h2 a") or block.select_one("h2")
            if h2:
                cn_name = h2.get_text(strip=True)
            h3 = block.select_one("h3")
            if h3:
                jp_name = h3.get_text(strip=True)

            # stats rows
            cost = ""
            power = ""
            race = ""
            for row in block.select(".meta .row-item"):
                label = row.select_one(".symbolHead")
                val = row.select_one(".value")
                label_text = label.get_text(strip=True) if label else ""
                value_text = val.get_text(strip=True) if val else ""
                if label_text == "费用":
                    cost = value_text
                elif label_text == "力量":
                    power = value_text
                elif label_text == "种族":
                    race = value_text

            # effect text
            text_full = ""
            eff = block.select_one("p.effect")
            if eff:
                # replace <br> with newlines
                for br in eff.find_all("br"):
                    br.replace_with("\n")
                text_full = eff.get_text(" ", strip=True)

            # image (optional)
            img = ""
            # Look back to previous sibling column for image
            parent_row = block.find_parent("div", class_="ant-row")
            if parent_row:
                img_el = parent_row.select_one("img")
                if img_el and img_el.get("src"):
                    img = img_el["src"].strip()

            # detail url from h2 link
            detail_url = ""
            if h2 and h2.name == "a":
                detail_url = h2.get("href", "").strip()
                if detail_url.startswith("/"):
                    detail_url = "https://zxcard.yimieji.com" + detail_url

            rows.append({
                "color": color,
                "card_number": card_number,
                "series": "",
                "rarity": rarity,
                "type": ctype,
                "jp_name": jp_name,
                "cn_name": cn_name,
                "cost": cost,
                "power": power,
                "race": race,
                "note": "",
                "text_full": text_full,
                "image_url": img,
                "detail_url": detail_url,
            })
        except Exception:
            continue
    return rows


def parse_list_pages_to_full(max_pages: Optional[int] = None) -> int:
    files = sorted(glob.glob(os.path.join(DEBUG_DIR, "yimieji_page_*.html")), key=lambda p: int(re.search(r"(\d+)", p).group(1)))
    if max_pages:
        files = files[:max_pages]
    write_full_csv_header(FULL_OUTPUT_CSV)
    total = 0
    seen = set()
    for path in files:
        with open(path, "r", encoding="utf-8") as f:
            html = f.read()
        rows = parse_list_cards_to_full(html)
        unique: List[Dict[str, str]] = []
        for r in rows:
            key = (r.get("card_number", ""), r.get("cn_name", ""))
            if key in seen:
                continue
            seen.add(key)
            unique.append(r)
        append_full_rows(FULL_OUTPUT_CSV, unique)
        total += len(unique)
        print(f"List->Full parsed {len(unique)} from {os.path.basename(path)} (full total {total})")
    return total


def run_detail_pipeline(max_pages: Optional[int] = None, max_items: Optional[int] = None) -> None:
    ensure_detail_dir()
    write_full_csv_header(FULL_OUTPUT_CSV)

    queue = build_detail_queue_from_list(max_pages=max_pages)
    if max_items:
        queue = queue[:max_items]

    done = set()
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                done = set(json.load(f).get("done", []))
        except Exception:
            done = set()

    # Prefer requests, fallback to Selenium only when needed
    session = build_requests_session()
    driver: Optional[webdriver.Chrome] = None

    try:
        rows_batch: List[Dict[str, str]] = []
        for idx, item in enumerate(queue, 1):
            url = item["detail_url"]
            number = item.get("card_number", "")
            out_path = detail_path_for(url, number)

            need_fetch = True
            if os.path.exists(out_path):
                need_fetch = False

            if need_fetch:
                ok = fetch_detail_requests(session, url, out_path, retries=4)
                if not ok:
                    # lazy init selenium driver only if strictly needed
                    if driver is None:
                        driver = create_driver(headless=True)
                    ok = fetch_detail(driver, url, out_path, retries=3)
                    if not ok:
                        continue

            with open(out_path, "r", encoding="utf-8") as f:
                html = f.read()
            row = parse_detail_html(html, url)
            if row.get("card_number") or row.get("cn_name") or row.get("jp_name"):
                rows_batch.append(row)

            if len(rows_batch) >= 50:
                append_full_rows(FULL_OUTPUT_CSV, rows_batch)
                rows_batch = []
                with open(STATE_FILE, "w", encoding="utf-8") as sf:
                    json.dump({"done": list(done | {out_path})}, sf)
            jitter_sleep(0.8, 0.5)

        if rows_batch:
            append_full_rows(FULL_OUTPUT_CSV, rows_batch)
            with open(STATE_FILE, "w", encoding="utf-8") as sf:
                json.dump({"done": list(done)}, sf)
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass


def auto_scroll_until_stable(driver: webdriver.Chrome, count_selector: str, stable_rounds: int = 3, max_rounds: int = 100) -> None:
    stable = 0
    last_count = -1
    combined_selector = f"{count_selector}, h2 a[href^='/Cards/']"
    for i in range(max_rounds):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        jitter_sleep(0.8, 0.5)
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        count = len(soup.select(combined_selector))
        if count == last_count:
            stable += 1
        else:
            stable = 0
        last_count = count
        print(f"scroll {i+1}: items={count}, stable={stable}/{stable_rounds}")
        if stable >= stable_rounds:
            break


def crawl_package_pages(
    package_urls: List[str],
    start_from: str = None,
    stable_rounds: int = 3,
    max_rounds: int = 150,
    record_zero_path: str = os.path.join(DEBUG_DIR, "zero_packages.txt"),
) -> int:
    ensure_dirs()
    write_full_csv_header(FULL_OUTPUT_CSV) if not os.path.exists(FULL_OUTPUT_CSV) else None
    driver = create_driver(headless=True)
    total_new = 0
    started = start_from is None
    
    try:
        for url in package_urls:
            safe_name = re.sub(r"[^a-zA-Z0-9]", "_", url.split("#")[0].rstrip("/").split("/")[-1])
            
            # 断点续跑：如果指定了起始包，跳过之前的包
            if start_from and not started:
                if safe_name == start_from:
                    started = True
                    print(f"Resuming from package: {safe_name}")
                else:
                    print(f"Skipping package: {safe_name}")
                    continue
            
            print(f"Open package: {url}")
            
            # 增加重试机制
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    driver.get(url)
                    try:
                        WebDriverWait(driver, EXPLICIT_WAIT_SEC).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                    except TimeoutException:
                        pass
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        print(f"Attempt {attempt + 1} failed for {safe_name}: {e}, retrying...")
                        time.sleep(5)
                        # 重新创建driver
                        try:
                            driver.quit()
                        except:
                            pass
                        driver = create_driver(headless=True)
                    else:
                        print(f"Failed to load {safe_name} after {max_retries} attempts: {e}")
                        break
            else:
                continue  # 如果所有重试都失败了，跳过这个包
            
            auto_scroll_until_stable(
                driver,
                count_selector="div.ant-col.ant-col-24.ant-col-lg-20",
                stable_rounds=stable_rounds,
                max_rounds=max_rounds,
            )
            html = driver.page_source
            out_path = os.path.join(DEBUG_DIR, f"package_{safe_name}.html")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(html)
            rows = parse_list_cards_to_full(html)
            if not rows:
                # 记录空结果的包用于之后重试
                try:
                    with open(record_zero_path, "a", encoding="utf-8") as zf:
                        zf.write(url + "\n")
                except Exception:
                    pass
                # Fallback: build minimal rows from card links
                soup = BeautifulSoup(html, "html.parser")
                for a in soup.select("h2 a[href^='/Cards/']"):
                    cn_name = a.get_text(strip=True)
                    detail_url = a.get("href", "").strip()
                    if detail_url.startswith("/"):
                        detail_url = "https://zxcard.yimieji.com" + detail_url
                    rows.append({
                        "color": "",
                        "card_number": "",
                        "series": "",
                        "rarity": "",
                        "type": "",
                        "jp_name": "",
                        "cn_name": cn_name,
                        "cost": "",
                        "power": "",
                        "race": "",
                        "note": "",
                        "text_full": "",
                        "image_url": "",
                        "detail_url": detail_url,
                    })
            append_full_rows(FULL_OUTPUT_CSV, rows)
            total_new += len(rows)
            print(f"Package {safe_name}: parsed {len(rows)} cards (cumulative {total_new})")
            jitter_sleep(2.0, 1.0)  # 增加延迟避免超时
    finally:
        try:
            driver.quit()
        except Exception:
            pass
    return total_new


def discover_package_urls() -> List[str]:
    session = build_requests_session()
    url = "https://zxcard.yimieji.com/package"
    print(f"Fetch package index: {url}")
    try:
        resp = session.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        urls = []
        for a in soup.select("a[href^='/Package/']"):
            href = a.get("href", "").strip()
            if href.startswith("/"):
                href = "https://zxcard.yimieji.com" + href
            if href not in urls:
                urls.append(href)
        print(f"Discovered {len(urls)} package URLs")
        return urls
    except Exception as e:
        print(f"Failed to fetch package index: {e}")
        return []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["list_full", "package", "full", "dedupe"], default="list_full")
    parser.add_argument("--pkg", nargs="*", help="package URLs like https://zxcard.yimieji.com/Package/B01#...")
    parser.add_argument("--resume-from", help="resume from specific package name (e.g., B34)")
    parser.add_argument("--retry-zero", action="store_true", help="retry packages recorded with zero parsed last run")
    parser.add_argument("--max-scroll", type=int, default=150, help="max scroll rounds")
    parser.add_argument("--stable-rounds", type=int, default=3, help="stable rounds threshold")
    # dedupe
    parser.add_argument("--in", dest="in_path", help="input CSV for dedupe, default to zx2_cards_full.csv")
    parser.add_argument("--out", dest="out_path", help="output CSV for dedupe, default to zx2_cards_full_deduped.csv")
    parser.add_argument("--key", dest="dedupe_key", choices=["auto", "detail_url", "image_url", "card"], default="auto", help="dedupe key strategy")
    args = parser.parse_args()

    if args.mode == "package":
        urls = args.pkg or []
        zero_path = os.path.join(DEBUG_DIR, "zero_packages.txt")
        if args.retry_zero and os.path.exists(zero_path):
            with open(zero_path, "r", encoding="utf-8") as f:
                urls = [line.strip() for line in f if line.strip()]
        if len(urls) == 1 and urls[0].upper() == "ALL":
            urls = discover_package_urls()
        if not urls:
            print("No package URLs provided via --pkg (or discovery failed)")
            return
        # 若是重试空包，先清空记录，避免死循环
        if args.retry_zero and os.path.exists(zero_path):
            try:
                os.remove(zero_path)
            except Exception:
                pass
        crawl_package_pages(
            urls,
            start_from=args.resume_from,
            stable_rounds=args.stable_rounds,
            max_rounds=args.max_scroll,
        )
        return

    if args.mode == "list_full":
        # Parse existing list pages into full CSV
        parse_list_pages_to_full(max_pages=None)
        return

    if args.mode == "full":
        fetch_html_pages(max_pages=None)
        parse_saved_htmls(max_pages=None)
        parse_list_pages_to_full(max_pages=None)
        return

    if args.mode == "dedupe":
        in_path = args.in_path or FULL_OUTPUT_CSV
        out_path = args.out_path or os.path.splitext(in_path)[0] + "_deduped.csv"
        key_strategy = args.dedupe_key
        deduped, total = dedupe_csv_file(in_path, out_path, key_strategy)
        print(f"Dedupe done: kept {deduped}/{total} → {out_path}")
        return


if __name__ == "__main__":
    main()
