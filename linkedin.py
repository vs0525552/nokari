from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import random

# 🔧 Configuration
LINKEDIN_USERNAME = "your_email@example.com"
LINKEDIN_PASSWORD = "your_password"
JOB_KEYWORDS = "java"
LOCATION = "pune"
MAX_PAGES = 2

# 🧠 Set up Chrome options
options = Options()
options.add_argument("--start-maximized")
options.add_argument("--disable-blink-features=AutomationControlled")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# 🧭 Log into LinkedIn
def login():
    driver.get("https://www.linkedin.com/login")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "username"))).send_keys(LINKEDIN_USERNAME)
    driver.find_element(By.ID, "password").send_keys(LINKEDIN_PASSWORD)
    driver.find_element(By.XPATH, "//button[@type='submit']").click()
    print("🔐 Logged in successfully.")
    time.sleep(5)

# 🔍 Search for jobs
def search_jobs():
    driver.get("https://www.linkedin.com/jobs")
    time.sleep(3)
    keyword_input = driver.find_element(By.XPATH, "//input[@aria-label='Search by title, skill, or company']")
    location_input = driver.find_element(By.XPATH, "//input[@aria-label='City, state, or zip code']")

    keyword_input.clear()
    keyword_input.send_keys(JOB_KEYWORDS)
    location_input.clear()
    location_input.send_keys(LOCATION)

    location_input.submit()
    time.sleep(5)

# 📩 Apply to jobs with Easy Apply
def apply_jobs():
    applied = 0
    for page in range(1, MAX_PAGES + 1):
        print(f"\n📄 Processing page {page}...")

        try:
            job_listings = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".jobs-search-results__list-item"))
            )
        except:
            print("❌ No job listings found.")
            continue

        for idx, job in enumerate(job_listings, 1):
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", job)
                time.sleep(1)
                job.click()
                time.sleep(2)

                job_title_elem = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h2.jobs-unified-top-card__job-title"))
                )
                job_title = job_title_elem.text.lower().strip()

                if JOB_KEYWORDS.lower() not in job_title:
                    print(f"⏭️ Skipping job #{idx} — title doesn't match: {job_title}")
                    continue

                print(f"\n🔍 Applying to job #{idx}: {job_title}")

                try:
                    easy_apply_btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Easy Apply')]"))
                    )
                    easy_apply_btn.click()
                    time.sleep(2)

                    submit_btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[@type='submit' and contains(., 'Submit')]"))
                    )
                    submit_btn.click()
                    print("✅ Applied successfully.")
                    applied += 1
                    time.sleep(2)

                    # Close confirmation modal if exists
                    try:
                        close_btn = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.CLASS_NAME, "artdeco-modal__dismiss"))
                        )
                        close_btn.click()
                        time.sleep(1)
                    except:
                        pass

                except Exception as e:
                    print(f"⚠️ Could not apply: {e}")
                    try:
                        dismiss = driver.find_element(By.CLASS_NAME, "artdeco-modal__dismiss")
                        dismiss.click()
                    except:
                        pass
                    continue

            except Exception as e:
                print(f"❌ Error on job #{idx}: {e}")
                driver.save_screenshot(f"screenshot_error_job_{idx}_page_{page}.png")
                continue

        # 🔁 Go to next page
        try:
            next_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Page " + str(page + 1) + "']"))
            )
            driver.execute_script("arguments[0].click();", next_button)
            time.sleep(random.uniform(3, 5))
        except:
            print("⛔ No more pages.")
            break

    print(f"\n🎉 Done! Total jobs applied: {applied}")

# 🚀 Run everything
login()
search_jobs()
apply_jobs()
driver.quit()
