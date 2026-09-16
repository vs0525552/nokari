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
from webdriver_manager.chrome import ChromeDriverManager
import time
import random
import os
import sys
import re
from datetime import datetime
from zoneinfo import ZoneInfo          # Python 3.9+; use pytz if older

# ─────────────────────────────────────────────────────────────────────────────
# TIMEZONE
# ─────────────────────────────────────────────────────────────────────────────
IST = ZoneInfo("Asia/Kolkata")

def now_ist() -> str:
    """Return current IST timestamp as a readable string."""
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")

def log(msg: str) -> None:
    """Print a timestamped log line."""
    print(f"[{now_ist()}]  {msg}")

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
    options.add_argument("--start-maximized")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver

# ─────────────────────────────────────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────────────────────────────────────
def login(driver: webdriver.Chrome, wait: WebDriverWait) -> None:
    log("🔐  Logging into Naukri …")
    driver.get("https://www.naukri.com/")
    time.sleep(3)

    # Click Login link
    try:
        wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Login"))).click()
    except Exception:
        wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//a[contains(@href,'login') and contains(text(),'Login')]")
            )
        ).click()
    time.sleep(2)

    email_input = wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "//input[@placeholder='Enter your active Email ID / Username']")
        )
    )
    email_input.send_keys(EMAIL)
    driver.find_element(
        By.XPATH, "//input[@placeholder='Enter your password']"
    ).send_keys(PASSWORD)
    driver.find_element(
        By.XPATH, "//button[contains(text(),'Login')]"
    ).click()
    time.sleep(5)
    log("✅  Login successful.")

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
    """True if the job's experience range overlaps [MIN_EXP_YEARS, MAX_EXP_YEARS]."""
    min_e, max_e = parse_experience_text(exp_text)
    if min_e is None:
        return False        # can't determine — skip
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


# ── LAYER 2: card-level Easy-Apply check ──────────────────────────────────────
def is_easy_apply(card) -> bool:
    """
    NAUKRI-ONLY.  Returns False for ANY hint of an external redirect:
      • Button text contains known external phrases
      • Card has a CSS class that marks it as an external post
      • A redirect/external icon is present in the card DOM
    """
    # Check 1: apply-button text
    try:
        btn = card.find_element(By.CLASS_NAME, "apply-button")
        txt = btn.text.strip().lower()
        if any(kw in txt for kw in EXTERNAL_KEYWORDS):
            return False
        # Button text must be in the allow-list to be considered easy-apply
        if txt and txt not in APPLY_BTN_ALLOWLIST:
            return False
    except Exception:
        pass   # no apply-button found on card — check other signals

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

    # Check 3: does the card contain an explicit "Apply on company site" text node?
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
) -> int:
    """
    Crawl Naukri results for *one* location and apply until MAX_APPLY is hit.
    Returns updated applied count.
    """
    url = build_search_url(location["slug"])
    label = location["label"]
    applied = applied_so_far
    page_num = 1

    log(separator())
    log(f"📍  Searching in: {label}")
    log(f"🔗  URL: {url}")
    driver.get(url)
    time.sleep(5)

    while applied < MAX_APPLY:
        log(separator("·"))
        log(f"📄  [{label}] Page {page_num} — ✅ Success: {applied}  ❌ Failed: {len(failure_log)}")

        # Wait for job listings
        try:
            wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "srp-jobtuple-wrapper"))
            )
        except Exception:
            driver.save_screenshot(f"search_error_{location['slug']}_p{page_num}.png")
            log(f"❌  No job listings found on page {page_num}. Screenshot saved. Moving on.")
            break

        job_cards = driver.find_elements(By.CLASS_NAME, "srp-jobtuple-wrapper")
        if not job_cards:
            log("⚠️   No job cards on this page. Moving to next location.")
            break

        log(f"🃏  Found {len(job_cards)} job card(s) on page {page_num}.")

        for idx, card in enumerate(job_cards, 1):
            if applied >= MAX_APPLY:
                log(f"🎯  Target of {MAX_APPLY} applications reached!")
                return applied

            job_title = ""
            exp_text  = ""
            job_url   = ""

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
                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", card
                )
                time.sleep(random.uniform(1.0, 2.0))
                job_url = card.find_element(By.TAG_NAME, "a").get_attribute("href") or ""

                if not is_naukri_url(job_url):
                    reason = f"Card href is off-Naukri: {job_url[:80]}"
                    log(f"  🚫  LAYER-1 BLOCKED | Card #{idx}: {reason}")
                    failure_log.append({
                        "title": job_title, "exp": exp_text,
                        "location": label, "reason": reason, "url": job_url
                    })
                    continue

                # ── Open in new tab ───────────────────────────────────────────
                driver.execute_script("window.open(arguments[0], '_blank');", job_url)
                time.sleep(2)

                if len(driver.window_handles) < 2:
                    reason = "New tab did not open"
                    log(f"  ⚠️   Card #{idx}: {reason}. Skipping.")
                    failure_log.append({
                        "title": job_title, "exp": exp_text,
                        "location": label, "reason": reason, "url": job_url
                    })
                    continue

                driver.switch_to.window(driver.window_handles[-1])
                time.sleep(2)

                # ── LAYER 3: Tab URL check — close & skip if not naukri.com ──
                current_url = driver.current_url
                if not is_naukri_url(current_url):
                    reason = f"Tab landed on external site: {current_url[:80]}"
                    log(f"  🚫  LAYER-3 BLOCKED | Card #{idx}: {reason}")
                    failure_log.append({
                        "title": job_title, "exp": exp_text,
                        "location": label, "reason": reason, "url": job_url
                    })
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])
                    continue

                # ── Verify experience on detail page ──────────────────────────
                try:
                    detail_exp = driver.find_element(
                        By.XPATH,
                        "//div[contains(@class,'exp')]//span | "
                        "//label[text()='Experience']/following-sibling::span"
                    ).text.strip()
                    if detail_exp and not is_experience_in_range(detail_exp):
                        reason = f"Detail-page exp '{detail_exp}' out of range"
                        log(f"  ⏭️   Card #{idx}: {reason}. Skipping.")
                        failure_log.append({
                            "title": job_title, "exp": detail_exp,
                            "location": label, "reason": reason, "url": job_url
                        })
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])
                        continue
                except Exception:
                    pass    # no detail exp element — proceed

                # ── LAYER 4: Strict Apply button allow-list ───────────────────
                # Only click a button whose normalised text is in APPLY_BTN_ALLOWLIST.
                # Reject anything mentioning company / site / external / redirect.
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

                        # Reject if any external keyword appears in button text
                        if any(kw in btn_text for kw in EXTERNAL_KEYWORDS):
                            log(
                                f"  🚫  LAYER-4 BLOCKED | Card #{idx}: "
                                f"Button text '{btn_text}' is external. Skipping."
                            )
                            clicked = False
                            break   # no point checking other selectors

                        # Reject if button text is NOT in the allowed set
                        if btn_text not in APPLY_BTN_ALLOWLIST:
                            log(
                                f"  🚫  LAYER-4 BLOCKED | Card #{idx}: "
                                f"Button text '{btn_text}' not in allow-list. Skipping."
                            )
                            clicked = False
                            break

                        driver.execute_script("arguments[0].click();", btn)
                        clicked = True
                        break
                    except Exception:
                        continue

                if clicked:
                    time.sleep(2)

                    # ── LAYER 5: Post-click URL — confirm still on naukri.com ─
                    post_click_url = driver.current_url
                    if not is_naukri_url(post_click_url):
                        reason = f"Apply click navigated off Naukri: {post_click_url[:80]}"
                        log(f"  🚫  LAYER-5 BLOCKED | Card #{idx}: {reason}")
                        failure_log.append({
                            "title": job_title, "exp": exp_text,
                            "location": label, "reason": reason, "url": job_url
                        })
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])
                        continue

                    # Dismiss any post-apply pop-up (e.g. profile update prompt)
                    for dismiss_xpath in [
                        "//button[contains(text(),'Skip')]",
                        "//button[contains(text(),'Not Now')]",
                        "//button[contains(text(),'Close')]",
                    ]:
                        try:
                            WebDriverWait(driver, 3).until(
                                EC.element_to_be_clickable((By.XPATH, dismiss_xpath))
                            ).click()
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
                        f"  ✅  APPLIED [{applied}/{MAX_APPLY}] → '{job_title}' "
                        f"| Exp: {exp_text or 'N/A'} | {label} | {now_ist()}"
                    )
                else:
                    reason = "Apply button not found or text not in allow-list (external guard)"
                    log(f"  🚫  Card #{idx}: {reason} → '{job_title}'. Skipping.")
                    failure_log.append({
                        "title": job_title, "exp": exp_text,
                        "location": label, "reason": reason, "url": job_url
                    })

            except Exception as exc:
                screenshot = f"error_{location['slug']}_p{page_num}_card{idx}.png"
                driver.save_screenshot(screenshot)
                reason = str(exc)[:120]
                log(f"  ❌  Card #{idx}: Unexpected error — {reason}. Screenshot: {screenshot}")
                failure_log.append({
                    "title":    job_title or "Unknown",
                    "exp":      exp_text,
                    "location": label,
                    "reason":   reason,
                    "url":      job_url,
                })

            finally:
                # Always close the job tab and return to results
                try:
                    if len(driver.window_handles) > 1:
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])
                except Exception:
                    pass
                time.sleep(random.uniform(1.5, 3.0))

        # ── Pagination ──────────────────────────────────────────────────────────
        if applied >= MAX_APPLY:
            break

        try:
            next_btn = driver.find_element(By.XPATH, "//a[span[text()='Next']]")
            cls = next_btn.get_attribute("class") or ""
            if "disabled" in cls:
                log(f"  ⏹️   No more pages for {label}.")
                break
            driver.execute_script("arguments[0].click();", next_btn)
            page_num += 1
            time.sleep(5)
        except Exception:
            log(f"  ⏹️   Next button not found — last page for {label}.")
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

    print("=" * 70)
    print("       NAUKRI AUTO-APPLY  —  JAVA DEVELOPER  (0–3 YRS)")
    print("=" * 70)
    log(f"🚀  Session started")
    log(f"   Target      : {MAX_APPLY} applications")
    log(f"   Experience  : {MIN_EXP_YEARS}–{MAX_EXP_YEARS} years")
    log(f"   Posted      : Last {POSTED_DAYS} days")
    log(f"   Locations   : Pune, Mumbai")
    log(f"   Apply type  : Easy Apply (Naukri-native) only")
    log(f"   Headless    : {headless}")
    print("=" * 70)

    success_log: list = []
    failure_log: list = []

    driver = build_driver(headless=headless)
    wait   = WebDriverWait(driver, 15)

    try:
        login(driver, wait)
        applied = 0

        # Run search for each location in sequence
        for loc in LOCATIONS:
            if applied >= MAX_APPLY:
                log(f"🎯  Target reached before scanning {loc['label']}. Done.")
                break
            applied = apply_for_location(
                driver, wait, loc, applied, success_log, failure_log
            )

        if applied < MAX_APPLY:
            log(
                f"⚠️   Could only apply to {applied}/{MAX_APPLY} jobs across "
                f"Pune + Mumbai in the last {POSTED_DAYS} days."
            )

    except Exception as exc:
        log(f"💥  Fatal error: {exc}")
        driver.save_screenshot("fatal_error.png")
        failure_log.append({
            "title": "FATAL", "exp": "", "location": "",
            "reason": str(exc)[:120], "url": ""
        })
        raise

    finally:
        driver.quit()
        print_summary(success_log, failure_log, start_time)


if __name__ == "__main__":
    main()
