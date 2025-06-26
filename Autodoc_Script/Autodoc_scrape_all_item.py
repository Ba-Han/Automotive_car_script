from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import csv
import itertools
from pprint import pprint

# === Setup Selenium WebDriver ===
options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

service = Service('/usr/local/bin/chromedriver')  # Adjust path if needed
driver = webdriver.Chrome(service=service, options=options)
wait = WebDriverWait(driver, 20)

BASE_URL = "https://www.autodoc.co.uk"
CATEGORY_URL = f"{BASE_URL}/tyres"

# === Step 1: Get product links ===
driver.get(CATEGORY_URL)
time.sleep(5)
driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
time.sleep(5)

product_elements = driver.find_elements(By.CSS_SELECTOR, 'a.product-card-grid__product-img')
product_links = [elem.get_attribute("href") for elem in product_elements if elem.get_attribute("href")]
#product_links = product_links[:1]  # Only first 1

print(f"Scraping found {len(product_links)} products...")

# === scrape_product function ===
def scrape_product(url):
    driver.get(url)
    try:
        wait.until(EC.element_to_be_clickable((By.ID, "banner-accept"))).click()
    except:
        pass

    time.sleep(2)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    product_data = []
    item_number = None  # Initialize item number

    # Force all hidden items to be displayed
    driver.execute_script("""
        document.querySelectorAll('[data-show-elements-item]').forEach(function(el) {
            el.style.display = 'block';
        });
    """)

    # Extract product description list
    try:
        description_items = driver.find_elements(By.CSS_SELECTOR, "ul.product-description__list li.product-description__item")
        for li in description_items:
            try:
                title_tag = li.find_element(By.CSS_SELECTOR, "span.product-description__item-title")
                value_tag = li.find_element(By.CSS_SELECTOR, "span.product-description__item-value")
                key = title_tag.text.strip().replace(":", "")
                value = value_tag.text.strip()

                if "Item number" in key:
                    item_number = value

            except Exception as e:
                print(f"Error parsing description item: {e}")
    except Exception as e:
        print(f"Error locating product description list: {e}")

    # Extract brand → model → engine info
    try:
        brands = driver.find_elements(By.CSS_SELECTOR, ".product-info-block__item-title")
        for i in range(len(brands)):
            brands = driver.find_elements(By.CSS_SELECTOR, ".product-info-block__item-title")
            brand = brands[i]
            brand_name = brand.text.strip()
            driver.execute_script("arguments[0].click();", brand)
            time.sleep(1)

            target_id = brand.get_attribute("data-target")
            model_ul = driver.find_element(By.CSS_SELECTOR, f"{target_id}.product-info-block__item-list")
            models = model_ul.find_elements(By.CSS_SELECTOR, "[data-toggle-model]")

            for model in models:
                model_name = model.text.strip()
                driver.execute_script("arguments[0].click();", model)
                time.sleep(0.5)

                model_target_id = model.get_attribute("data-target")
                try:
                    engine_ul = driver.find_element(By.CSS_SELECTOR, f"{model_target_id}.product-info-block__item-sublist")
                    engines = engine_ul.find_elements(By.TAG_NAME, "li")
                    if engines:
                        for engine in engines:
                            product_data.append({
                                "Brand": brand_name,
                                "Model": model_name,
                                "Engine Data": engine.text.strip()
                            })
                    else:
                        product_data.append({
                            "Brand": brand_name,
                            "Model": model_name,
                            "Engine Data": "No engine data"
                        })
                except:
                    product_data.append({
                        "Brand": brand_name,
                        "Model": model_name,
                        "Engine Data": "Engine info not found"
                    })

        # OE Number extraction
        try:
            oe_elements = driver.find_elements(By.CSS_SELECTOR, ".product-oem__list li")
            oe_list = [oe.text.strip() for oe in oe_elements if oe.text.strip()]
            oe_str = "; ".join(oe_list)
            for entry in product_data:
                entry["OE Number"] = oe_str
        except:
            pass

        # Summary table info
        summary = {}
        table = soup.find('table', class_='summary-table')
        if table:
            for row in table.find_all('tr'):
                cols = row.find_all('td')
                if len(cols) == 2:
                    k = cols[0].get_text(strip=True)
                    v = cols[1].get_text(strip=True)
                    summary[k] = v

        for entry in product_data:
            entry.update(summary)
            if item_number:
                entry["Item Number"] = item_number

    except Exception as e:
        print(f"❌ Error scraping {url}: {e}")

    return product_data

# === Scrape all product pages ===
all_data = []
for idx, link in enumerate(product_links, 1):
    print(f"→ Scraping product {idx}/{len(product_links)}: {link}")
    scraped = scrape_product(link)
    all_data.append(scraped)
    print(f"  → Collected {len(scraped)} rows.\n")

# === Flatten and preview ===
flat_data = list(itertools.chain.from_iterable(all_data))

if flat_data:
    #print("\n🔎 Preview of Scraped Data (first 3 rows):")
    #pprint(flat_data[:3])  # Show only first 3 rows

    # === Save to CSV ===
    default_columns = ["Item Number", "Brand", "Model", "Engine Data", "OE Number", "Car models", "Engines", "Engine power (horsepower)", "Power (kilowatts)", "Year of manufacture", "Manufacturer article number", "OE part number(s)"]
    fieldnames = default_columns

    with open("excel.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in flat_data:
            filtered_row = {k: row.get(k, "") for k in fieldnames}
            writer.writerow(filtered_row)

    print(f"\n✅ Saved {len(flat_data)} rows to 'excel.csv'")

# === Close Selenium ===
driver.quit()
