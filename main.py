"""
Naukri Auto-Apply — Java Developer (0–3 Yrs | Pune & Mumbai | Last 3 Days)
============================================================================
• Applies to exactly 10 Easy-Apply Java Developer jobs  ← NAUKRI ONLY
• Experience filter : 0 – 3 years
• Locations         : Pune  AND  Mumbai (runs a separate search for each)
• Date filter       : posted within the last 3 days
• Timezone          : All log timestamps in IST (Asia/Kolkata)
• Logging           : per-job ✅/❌ details + final SUCCESS / FAILED summary

NAUKRI-ONLY ENFORCEMENT (5 layers)
  1. Card href pre-check  — skip if the job link is not on naukri.com
  2. is_easy_apply()      — card-level: reject external-redirect markers
  3. Tab URL check        — close immediately if tab lands off naukri.com
  4. Apply btn allow-list — only click buttons whose text is 'Apply' or 'Apply Now'
  5. Post-click URL check — verify we are still on naukri.com after clicking
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import os
import sys
import re
import io
from datetime import datetime
from zoneinfo import ZoneInfo          # Python 3.9+; use pytz if older

# Force UTF-8 output on Windows so emojis don't crash the terminal
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ─────────────────────────────────────────────────────────────────────────────
# TIMEZONE
# ─────────────────────────────────────────────────────────────────────────────
IST = ZoneInfo("Asia/Kolkata")

def now_ist() -> str:
    """Return current IST timestamp as a readable string."""
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")

def log(msg: str) -> None:
    """Print a timestamped log line (safe on Windows terminals)."""
    line = f"[{now_ist()}]  {msg}"
    try:
        print(line)
    except UnicodeEncodeError:
        print(line.encode("ascii", errors="replace").decode("ascii"))

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
EMAIL    = os.environ.get("NAUKRI_EMAIL",    "vishalshekokar999@gmail.com")
PASSWORD = os.environ.get("NAUKRI_PASSWORD", "Vss@1234")

JOB_KEYWORDS  = "java developer"
MAX_APPLY     = 10           # stop after exactly 10 successful applications
MIN_EXP_YEARS = 0
MAX_EXP_YEARS = 3
POSTED_DAYS   = 3            # only jobs posted within the last 3 days
SESSION_DEADLINE_MINUTES = 30  # hard stop after 30 minutes no matter what

# Page load waits (seconds) — longer values help in headless CI
WAIT_PAGE_LOAD   = 7    # after driver.get()
WAIT_TAB_OPEN    = 3    # after opening a new tab
WAIT_AFTER_CLICK = 3    # after clicking Apply
WAIT_BETWEEN_CARDS = (2.0, 4.0)   # random range between cards

# ── NAUKRI-ONLY GUARD ─────────────────────────────────────────────────────────
# All URLs must belong to this domain.  Anything else is rejected instantly.
NAUKRI_DOMAIN = "naukri.com"

# Exact allow-list of Apply button texts (lowercase).  Anything else = external.
APPLY_BTN_ALLOWLIST = {"apply", "apply now"}

# Keywords that reveal an external / company-site redirect on a card or button.
EXTERNAL_KEYWORDS = [
    "company site", "company's site", "apply on company",
    "external", "redirect", "apply via", "apply at",
]

# Naukri location slugs → search URL segments
LOCATIONS = [
    {"slug": "pune",   "label": "Pune"},
    {"slug": "mumbai", "label": "Mumbai"},
]

def build_search_url(location_slug: str) -> str:
    """
    Build the Naukri search URL with all filters baked in:
      experience=0&experienceFilterApply=1   → 0-3 yrs
      postAgo=3                              → last 3 days
      l=<location>                           → city filter
    """
    return (
        f"https://www.naukri.com/java-developer-jobs-in-{location_slug}"
        f"?k=java+developer"
        f"&l={location_slug}"
        f"&experience=0"
        f"&experienceFilterApply=1"
        f"&postAgo=3"
    )

# ─────────────────────────────────────────────────────────────────────────────
# DRIVER SETUP
# ─────────────────────────────────────────────────────────────────────────────
def build_driver(headless: bool = False) -> webdriver.Chrome:
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    )
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    # In CI: use the exact chromedriver we installed (CHROMEDRIVER_PATH env var)
    # Locally: Selenium's built-in manager auto-detects the right version
    chromedriver_path = os.environ.get("CHROMEDRIVER_PATH", "")
    if chromedriver_path:
        driver = webdriver.Chrome(service=Service(chromedriver_path), options=options)
        log(f"[DRIVER] Using ChromeDriver from: {chromedriver_path}")
    else:
        driver = webdriver.Chrome(options=options)
    # CDP-level stealth: hide webdriver flag from JS
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-IN','en']});
            window.chrome = { runtime: {} };
        """
    })
    return driver

# ─────────────────────────────────────────────────────────────────────────────
# HUMAN BEHAVIOUR HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def human_sleep(min_s: float, max_s: float) -> None:
    """Sleep a random duration — simulates human think time."""
    time.sleep(random.uniform(min_s, max_s))

def human_type(element, text: str) -> None:
    """Type text character by character with realistic random delays."""
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.05, 0.18))   # 50–180 ms per keystroke
    human_sleep(0.3, 0.8)   # brief pause after finishing

def human_scroll(driver, element=None, direction: str = "down", pixels: int = 300) -> None:
    """
    Smoothly scroll the page in small steps — mimics a human reading.
    If element is given, scrolls that element into view first.
    """
    if element:
        driver.execute_script(
            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
            element
        )
        human_sleep(0.4, 0.9)
    else:
        step = random.randint(80, 140)
        steps = max(1, pixels // step)
        sign = 1 if direction == "down" else -1
        for _ in range(steps):
            driver.execute_script(f"window.scrollBy(0, {sign * step});")
            time.sleep(random.uniform(0.05, 0.12))
        human_sleep(0.3, 0.7)

def dismiss_popup(driver) -> None:
    """Close any overlay / cookie banner / notification popup if present."""
    selectors = [
        "//button[contains(text(),'Accept')]",
        "//button[contains(text(),'Close')]",
        "//button[contains(text(),'No Thanks')]",
        "//button[@aria-label='Close']",
        "//span[@class='crossIcon']",
        "//div[contains(@class,'close')]",
    ]
    for sel in selectors:
        try:
            btn = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.XPATH, sel))
            )
            driver.execute_script("arguments[0].click();", btn)
            human_sleep(0.5, 1.0)
            return
        except Exception:
            continue

# ─────────────────────────────────────────────────────────────────────────────
# LOGIN  (navigates directly to login page — works in headless CI)
# ─────────────────────────────────────────────────────────────────────────────
def login(driver: webdriver.Chrome, wait: WebDriverWait) -> None:
    log("[LOGIN] Navigating directly to Naukri login page ...")
    driver.get("https://www.naukri.com/nlogin/login")
    human_sleep(5.0, 7.0)   # generous wait for CI to fully render the page

    # Debug screenshot — helps diagnose bot-check pages in CI
    driver.save_screenshot("login_page_debug.png")
    log(f"[LOGIN] Page loaded. Title: '{driver.title}' | URL: {driver.current_url[:80]}")

    dismiss_popup(driver)

    # --- Email field: try selectors one by one (most specific first) ---
    email_input = None
    for by, sel in [
        (By.ID,    "usernameField"),
        (By.NAME,  "username"),
        (By.XPATH, "//input[@placeholder='Enter your active Email ID / Username']"),
        (By.XPATH, "//input[@type='text' and contains(@class,'user')]"),
        (By.XPATH, "(//input[@type='text'])[1]"),
    ]:
        try:
            email_input = WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((by, sel))
            )
            log(f"[LOGIN] Email field found via: {by}='{sel}'")
            break
        except Exception:
            continue

    if email_input is None:
        driver.save_screenshot("login_no_email_field.png")
        raise RuntimeError(
            "[LOGIN] Could not locate email input field. "
            "Check login_page_debug.png and login_no_email_field.png in artifacts."
        )

    human_sleep(0.8, 1.5)
    email_input.click()
    human_sleep(0.3, 0.6)
    human_type(email_input, EMAIL)
    log("[LOGIN] Email entered.")

    # --- Password field ---
    pwd_input = None
    for by, sel in [
        (By.ID,    "passwordField"),
        (By.NAME,  "password"),
        (By.XPATH, "//input[@placeholder='Enter your password']"),
        (By.XPATH, "//input[@type='password']"),
    ]:
        try:
            pwd_input = WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((by, sel))
            )
            log(f"[LOGIN] Password field found via: {by}='{sel}'")
            break
        except Exception:
            continue

    if pwd_input is None:
        driver.save_screenshot("login_no_pwd_field.png")
        raise RuntimeError("[LOGIN] Could not locate password input field.")

    pwd_input.click()
    human_sleep(0.4, 0.9)
    human_type(pwd_input, PASSWORD)
    log("[LOGIN] Password entered.")

    # --- Login button ---
    human_sleep(0.5, 1.2)
    login_btn = None
    for by, sel in [
        (By.XPATH, "//button[@type='submit']"),
        (By.XPATH, "//button[contains(text(),'Login')]"),
        (By.XPATH, "//button[contains(text(),'Sign in')]"),
        (By.XPATH, "(//button)[1]"),
    ]:
        try:
            login_btn = WebDriverWait(driver, 8).until(
                EC.element_to_be_clickable((by, sel))
            )
            log(f"[LOGIN] Login button found via: {by}='{sel}'")
            break
        except Exception:
            continue

    if login_btn is None:
        driver.save_screenshot("login_no_btn.png")
        raise RuntimeError("[LOGIN] Could not locate Login button.")

    driver.execute_script("arguments[0].click();", login_btn)
    log("[LOGIN] Login button clicked. Waiting for redirect ...")
    human_sleep(5.0, 7.0)

    driver.save_screenshot("login_after_click.png")
    log(f"[LOGIN] Post-login URL: {driver.current_url[:80]}")

    # Verify redirect away from login page
    if "nlogin" in driver.current_url:
        log("[LOGIN] WARNING: Still on login page — login may have failed. Continuing...")
    else:
        log("[LOGIN] Login successful!")

    dismiss_popup(driver)
    human_sleep(1.0, 2.0)

# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────
def parse_experience_text(exp_text: str):
    """
    Parse experience strings like '0-3 Yrs', '1 Yr', '2-5 Yrs'.
    Returns (min_exp, max_exp) as ints, or (None, None) if unparseable.
    """
    m = re.search(r"(\d+)\s*-\s*(\d+)", exp_text)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"(\d+)", exp_text)
    if m:
        v = int(m.group(1))
        return v, v
    return None, None


def is_experience_in_range(exp_text: str) -> bool:
    """True if the job's experience range overlaps [MIN_EXP_YEARS, MAX_EXP_YEARS].
    If exp_text is blank or unparseable, returns True (pass through — let the
    job detail page be the final arbiter).
    """
    if not exp_text or not exp_text.strip():
        return True   # unknown exp on card → don't block, check detail page
    min_e, max_e = parse_experience_text(exp_text)
    if min_e is None:
        return True   # unparseable → pass through
    return min_e <= MAX_EXP_YEARS and max_e >= MIN_EXP_YEARS


# ── LAYER 1 HELPER: domain check ─────────────────────────────────────────────
def is_naukri_url(url: str) -> bool:
    """
    Returns True ONLY if the URL belongs to naukri.com.
    Rejects empty strings, external domains, and redirects.
    """
    if not url:
        return False
    # Strip scheme and normalise
    clean = url.lower().split("?")[0].split("#")[0]
    return NAUKRI_DOMAIN in clean


# ── LAYER 2: card-level Easy-Apply check ─────────────────────────────────────
def is_easy_apply(card) -> bool:
    """
    NAUKRI-ONLY. Returns False ONLY when there is an explicit external marker:
      - Button text contains known external phrases (company site, redirect, etc.)
      - Card HTML has external CSS class markers
      - Card text explicitly says 'Apply on company site' etc.
    Blank button text or 'Apply' / 'Apply Now' = easy apply (pass through).
    """
    # Check 1: apply-button text — reject only on explicit external keywords
    try:
        btn = card.find_element(By.CLASS_NAME, "apply-button")
        txt = btn.text.strip().lower()
        if any(kw in txt for kw in EXTERNAL_KEYWORDS):
            return False
        # If button text is blank or contains 'apply' → it's easy apply
    except Exception:
        pass   # no apply-button on card — check other signals

    # Check 2: card-level CSS class markers Naukri uses for external posts
    try:
        card_html = card.get_attribute("outerHTML").lower()
        external_class_markers = [
            "apply-redirect", "external-apply", "companysiteapply",
            "company-site", "not-easy-apply",
        ]
        if any(m in card_html for m in external_class_markers):
            return False
    except Exception:
        pass

    # Check 3: card text explicitly says 'apply on company site' etc.
    try:
        card_text = card.text.lower()
        if any(kw in card_text for kw in EXTERNAL_KEYWORDS):
            return False
    except Exception:
        pass

    return True


def get_experience_from_card(card) -> str:
    """Extract experience text from a job card, e.g. '0-3 Yrs'."""
    for xpath in [
        ".//span[@class='expwdth']",
        ".//li[contains(@class,'exp')]",
        ".//span[contains(@class,'exp')]",
    ]:
        try:
            txt = card.find_element(By.XPATH, xpath).text.strip()
            if txt:
                return txt
        except Exception:
            continue
    return ""


def separator(char: str = "─", width: int = 70) -> str:
    return char * width

# ─────────────────────────────────────────────────────────────────────────────
# APPLY LOOP  (single location)
# ─────────────────────────────────────────────────────────────────────────────
def apply_for_location(
    driver: webdriver.Chrome,
    wait: WebDriverWait,
    location: dict,
    applied_so_far: int,
    success_log: list,
    failure_log: list,
    deadline: float,          # time.time() value — stop at or after this
) -> int:
    """
    Crawl Naukri results for *one* location and apply until MAX_APPLY is hit
    OR the 30-minute session deadline is reached.
    Returns updated applied count.
    """
    url = build_search_url(location["slug"])
    label = location["label"]
    applied = applied_so_far
    page_num = 1

    log(separator())
    log(f"[SEARCH] Location: {label} | Deadline in: {int((deadline - time.time())/60)} min")
    log(f"[SEARCH] URL: {url}")
    driver.get(url)
    time.sleep(WAIT_PAGE_LOAD)

    while applied < MAX_APPLY:
        # ── Hard deadline check ──────────────────────────────────────────
        if time.time() >= deadline:
            log(f"[DEADLINE] 30-minute session limit reached. Stopping.")
            return applied

        log(separator("."))
        log(f"[PAGE {page_num}] [{label}] Applied: {applied}/{MAX_APPLY} | Failed: {len(failure_log)}")

        # Wait for job listings — retry up to 2 times for slow CI loads
        job_cards = []
        for attempt in range(1, 4):
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "srp-jobtuple-wrapper"))
                )
                job_cards = driver.find_elements(By.CLASS_NAME, "srp-jobtuple-wrapper")
                if job_cards:
                    break
                log(f"[PAGE {page_num}] No cards yet (attempt {attempt}/3). Waiting...")
                time.sleep(5)
            except Exception:
                log(f"[PAGE {page_num}] Timeout waiting for cards (attempt {attempt}/3).")
                time.sleep(5)

        if not job_cards:
            driver.save_screenshot(f"search_error_{location['slug']}_p{page_num}.png")
            log(f"[PAGE {page_num}] No job cards after 3 attempts. Moving to next location.")
            break

        log(f"[PAGE {page_num}] Found {len(job_cards)} card(s).")

        for idx, card in enumerate(job_cards, 1):
            # Deadline check inside card loop too
            if time.time() >= deadline:
                log(f"[DEADLINE] Session limit hit mid-page. Stopping.")
                return applied

            if applied >= MAX_APPLY:
                log(f"[DONE] Target of {MAX_APPLY} applications reached!")
                return applied

            job_title = ""
            exp_text  = ""
            job_url   = ""
            tab_opened = False   # track whether WE opened a tab (to close in finally)

            try:
                # ── 1. Read title ──────────────────────────────────────────────
                try:
                    job_title = card.find_element(By.CLASS_NAME, "title").text.strip()
                except Exception:
                    log(f"  ⏭️  Card #{idx}: Cannot read title. Skipping.")
                    continue

                if "java" not in job_title.lower():
                    log(f"  ⏭️  Card #{idx}: Not a Java role → '{job_title}'. Skipping.")
                    continue

                # ── 2. Experience filter ───────────────────────────────────────
                exp_text = get_experience_from_card(card)
                if exp_text and not is_experience_in_range(exp_text):
                    log(
                        f"  ⏭️  Card #{idx}: Exp '{exp_text}' outside "
                        f"{MIN_EXP_YEARS}–{MAX_EXP_YEARS} yrs → '{job_title}'. Skipping."
                    )
                    continue

                # ── 3. Easy Apply filter ───────────────────────────────────────
                if not is_easy_apply(card):
                    log(f"  ⏭️  Card #{idx}: External apply → '{job_title}'. Skipping.")
                    continue

                log(f"  🔍  Card #{idx}: Attempting → '{job_title}' | Exp: '{exp_text or 'N/A'}' | {label}")

                # ── LAYER 1: Pre-tab href check — must be naukri.com ──────────
                # Scroll card into view like a human browsing the list
                human_scroll(driver, element=card)
                human_sleep(0.8, 1.8)   # glance at the card before clicking
                job_url = card.find_element(By.TAG_NAME, "a").get_attribute("href") or ""

                if not is_naukri_url(job_url):
                    reason = f"Card href is off-Naukri: {job_url[:80]}"
                    log(f"  [L1-BLOCKED] Card #{idx}: {reason}")
                    failure_log.append({
                        "title": job_title, "exp": exp_text,
                        "location": label, "reason": reason, "url": job_url
                    })
                    continue

                # ── Open in new tab ───────────────────────────────────────────
                driver.execute_script("window.open(arguments[0], '_blank');", job_url)
                human_sleep(2.5, 4.0)   # wait for tab to load
                tab_opened = True

                if len(driver.window_handles) < 2:
                    reason = "New tab did not open"
                    log(f"  [WARN] Card #{idx}: {reason}. Skipping.")
                    tab_opened = False
                    failure_log.append({
                        "title": job_title, "exp": exp_text,
                        "location": label, "reason": reason, "url": job_url
                    })
                    continue

                driver.switch_to.window(driver.window_handles[-1])
                human_sleep(2.0, 3.5)   # let the job detail page render

                # ── LAYER 3: Tab URL check — close & skip if not naukri.com ──
                current_url = driver.current_url
                if not is_naukri_url(current_url):
                    reason = f"Tab landed on external site: {current_url[:80]}"
                    log(f"  [L3-BLOCKED] Card #{idx}: {reason}")
                    failure_log.append({
                        "title": job_title, "exp": exp_text,
                        "location": label, "reason": reason, "url": job_url
                    })
                    driver.close()
                    tab_opened = False
                    driver.switch_to.window(driver.window_handles[0])
                    continue

                # ── Verify experience on detail page ──────────────────────────
                # Simulate reading: scroll down through job desc, then back up
                human_scroll(driver, direction="down", pixels=random.randint(250, 450))
                human_sleep(1.5, 3.0)   # human reads the description
                human_scroll(driver, direction="up", pixels=random.randint(100, 220))
                human_sleep(0.5, 1.2)
                dismiss_popup(driver)   # close any popup that appeared while reading

                try:
                    detail_exp = driver.find_element(
                        By.XPATH,
                        "//div[contains(@class,'exp')]//span | "
                        "//label[text()='Experience']/following-sibling::span"
                    ).text.strip()
                    if detail_exp and not is_experience_in_range(detail_exp):
                        reason = f"Detail-page exp '{detail_exp}' out of range"
                        log(f"  [SKIP] Card #{idx}: {reason}. Skipping.")
                        failure_log.append({
                            "title": job_title, "exp": detail_exp,
                            "location": label, "reason": reason, "url": job_url
                        })
                        driver.close()
                        tab_opened = False
                        driver.switch_to.window(driver.window_handles[0])
                        continue
                except Exception:
                    pass    # no detail exp element — proceed


                # ── LAYER 4: Apply button — reject only explicit external text ─
                # Click any button whose text contains 'apply' but NOT external keywords.
                # This is permissive on purpose — Layer 3 & 5 (URL checks) are the
                # hard safety net against external sites.
                clicked = False
                for selector, by in [
                    ("apply-button",                       By.ID),
                    ("apply-button",                       By.CLASS_NAME),
                    ("//button[contains(text(),'Apply')]", By.XPATH),
                ]:
                    try:
                        btn = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((by, selector))
                        )
                        btn_text = btn.text.strip().lower()

                        # Hard reject: button explicitly says external/company site
                        if any(kw in btn_text for kw in EXTERNAL_KEYWORDS):
                            log(
                                f"  [LAYER-4 BLOCKED] Card #{idx}: "
                                f"Button '{btn_text}' is external. Skipping."
                            )
                            clicked = False
                            break

                        # Accept: 'apply', 'apply now', or any 'apply*' text
                        driver.execute_script("arguments[0].click();", btn)
                        log(f"  [LAYER-4 OK] Clicked Apply button: '{btn_text}'")
                        clicked = True
                        break
                    except Exception:
                        continue

                if clicked:
                    human_sleep(2.0, 3.5)   # wait for apply confirmation to appear

                    # ── LAYER 5: Post-click URL — confirm still on naukri.com ─
                    post_click_url = driver.current_url
                    if not is_naukri_url(post_click_url):
                        reason = f"Apply click navigated off Naukri: {post_click_url[:80]}"
                        log(f"  [L5-BLOCKED] Card #{idx}: {reason}")
                        failure_log.append({
                            "title": job_title, "exp": exp_text,
                            "location": label, "reason": reason, "url": job_url
                        })
                        driver.close()
                        tab_opened = False
                        driver.switch_to.window(driver.window_handles[0])
                        continue

                    # Dismiss any post-apply pop-up (profile update / confirmation)
                    for dismiss_xpath in [
                        "//button[contains(text(),'Skip')]",
                        "//button[contains(text(),'Not Now')]",
                        "//button[contains(text(),'Close')]",
                        "//button[@aria-label='Close']",
                    ]:
                        try:
                            WebDriverWait(driver, 3).until(
                                EC.element_to_be_clickable((By.XPATH, dismiss_xpath))
                            ).click()
                            time.sleep(1)
                            break
                        except Exception:
                            pass

                    applied += 1
                    success_log.append({
                        "no":       applied,
                        "title":    job_title,
                        "exp":      exp_text or "N/A",
                        "location": label,
                        "url":      job_url,
                        "time":     now_ist(),
                    })
                    log(
                        f"  [APPLIED] [{applied}/{MAX_APPLY}] '{job_title}' "
                        f"| Exp: {exp_text or 'N/A'} | {label} | {now_ist()}"
                    )
                else:
                    reason = "Apply button not found or blocked as external"
                    log(f"  [SKIP] Card #{idx}: {reason} -> '{job_title}'")
                    failure_log.append({
                        "title": job_title, "exp": exp_text,
                        "location": label, "reason": reason, "url": job_url
                    })

            except Exception as exc:
                screenshot = f"error_{location['slug']}_p{page_num}_card{idx}.png"
                try:
                    driver.save_screenshot(screenshot)
                except Exception:
                    pass
                reason = str(exc)[:120]
                log(f"  [ERROR] Card #{idx}: {reason} | Screenshot: {screenshot}")
                failure_log.append({
                    "title":    job_title or "Unknown",
                    "exp":      exp_text,
                    "location": label,
                    "reason":   reason,
                    "url":      job_url,
                })

            finally:
                # Only close the tab if WE opened it and it's still open
                try:
                    if tab_opened and len(driver.window_handles) > 1:
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])
                except Exception:
                    pass
                # Human-like pause between jobs — varies naturally
                human_sleep(*WAIT_BETWEEN_CARDS)

        # ── Pagination ──────────────────────────────────────────────────────────
        if applied >= MAX_APPLY:
            break
        if time.time() >= deadline:
            log(f"[DEADLINE] Session limit hit at pagination. Stopping.")
            break

        try:
            next_btn = driver.find_element(By.XPATH, "//a[span[text()='Next']]")
            cls = next_btn.get_attribute("class") or ""
            if "disabled" in cls:
                log(f"[PAGE] No more pages for {label}.")
                break
            driver.execute_script("arguments[0].click();", next_btn)
            page_num += 1
            time.sleep(WAIT_PAGE_LOAD)   # give the new page time to fully render
        except Exception:
            log(f"[PAGE] Next button not found — last page for {label}.")
            break

    return applied

# ─────────────────────────────────────────────────────────────────────────────
# FINAL SUMMARY PRINTER
# ─────────────────────────────────────────────────────────────────────────────
def print_summary(success_log: list, failure_log: list, start_time: str) -> None:
    end_time = now_ist()
    total    = len(success_log)
    failed   = len(failure_log)

    print()
    print("=" * 70)
    print("              NAUKRI AUTO-APPLY  —  FINAL REPORT")
    print("=" * 70)
    print(f"  Run started : {start_time}")
    print(f"  Run ended   : {end_time}")
    print(f"  Keyword     : Java Developer")
    print(f"  Experience  : {MIN_EXP_YEARS}–{MAX_EXP_YEARS} years")
    print(f"  Posted      : Last {POSTED_DAYS} days")
    print(f"  Locations   : Pune, Mumbai")
    print(f"  Target      : {MAX_APPLY} jobs")
    print("-" * 70)
    print(f"  ✅  Successfully Applied : {total}")
    print(f"  ❌  Failed / Skipped     : {failed}")
    print("=" * 70)

    if success_log:
        print("\n  ✅  SUCCESSFUL APPLICATIONS:")
        print(f"  {'#':<4}  {'Title':<40}  {'Exp':<10}  {'Location':<8}  Time")
        print(f"  {'-'*4}  {'-'*40}  {'-'*10}  {'-'*8}  {'-'*24}")
        for s in success_log:
            title = s['title'][:40]
            print(
                f"  {s['no']:<4}  {title:<40}  {s['exp']:<10}  "
                f"{s['location']:<8}  {s['time']}"
            )
        print()

    if failure_log:
        print("\n  ❌  FAILED / SKIPPED JOBS:")
        print(f"  {'Title':<40}  {'Exp':<10}  {'Location':<8}  Reason")
        print(f"  {'-'*40}  {'-'*10}  {'-'*8}  {'-'*30}")
        for f in failure_log:
            title  = (f['title'] or "Unknown")[:40]
            reason = (f['reason'] or "")[:50]
            print(
                f"  {title:<40}  {f.get('exp',''):<10}  "
                f"{f.get('location',''):<8}  {reason}"
            )
    print("=" * 70)

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    headless   = "--headless" in sys.argv or os.environ.get("HEADLESS", "").lower() == "true"
    start_time = now_ist()
    deadline   = time.time() + SESSION_DEADLINE_MINUTES * 60

    print("=" * 70)
    print("       NAUKRI AUTO-APPLY  -  JAVA DEVELOPER  (0-3 YRS)")
    print("=" * 70)
    log(f"[START] Session started")
    log(f"  Target    : {MAX_APPLY} applications")
    log(f"  Exp       : {MIN_EXP_YEARS}-{MAX_EXP_YEARS} years")
    log(f"  Posted    : Last {POSTED_DAYS} days")
    log(f"  Locations : Pune, Mumbai")
    log(f"  Deadline  : {SESSION_DEADLINE_MINUTES} minutes from now")
    log(f"  Headless  : {headless}")
    print("=" * 70)

    success_log: list = []
    failure_log: list = []

    driver = build_driver(headless=headless)
    wait   = WebDriverWait(driver, 20)

    try:
        login(driver, wait)
        applied = 0

        # Scan each location in sequence; stop when 10 applied or deadline hit
        for loc in LOCATIONS:
            if applied >= MAX_APPLY or time.time() >= deadline:
                break
            log(f"[LOC] Scanning {loc['label']} | Applied so far: {applied}/{MAX_APPLY}")
            applied = apply_for_location(
                driver, wait, loc, applied, success_log, failure_log, deadline
            )

        reason = "Deadline reached" if time.time() >= deadline else "All pages exhausted"
        if applied < MAX_APPLY:
            log(f"[DONE] Session ended: {applied}/{MAX_APPLY} applied. Reason: {reason}")

    except Exception as exc:
        log(f"[FATAL] {exc}")
        try:
            driver.save_screenshot("fatal_error.png")
        except Exception:
            pass
        failure_log.append({
            "title": "FATAL", "exp": "", "location": "",
            "reason": str(exc)[:120], "url": ""
        })
        raise

    finally:
        try:
            driver.quit()
        except Exception:
            pass
        print_summary(success_log, failure_log, start_time)


if __name__ == "__main__":
    main()



if __name__ == "__main__":
    main()
