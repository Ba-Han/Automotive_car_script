#install_list
#!pip install selenium webdriver-manager

#if you want to run the script in google colab
#!wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
#!dpkg -i google-chrome-stable_current_amd64.deb
#!apt-get -f install -y

#check the install version
#!google-chrome --version

#!wget -q https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/136.0.7103.92/linux64/chromedriver-linux64.zip
#!unzip -o chromedriver-linux64.zip
#!mv -f chromedriver-linux64/chromedriver /usr/local/bin/chromedriver
#!chmod +x /usr/local/bin/chromedriver

#chefk the install version
#!chromedriver --version

#run the script in VS-Code
#Python Car245_scrape_product_info.py

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import csv

# === Setup Selenium WebDriver ===
options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

service = Service('/usr/local/bin/chromedriver')  # Adjust path if needed
driver = webdriver.Chrome(service=service, options=options)
wait = WebDriverWait(driver, 20)

BASE_URL = "https://www.autodoc.co.uk"
CATEGORY_URL = f"{BASE_URL}/car-parts/brake-power-regulator-10137"

# === Step 1: Get All Product Links from Category Page ===
driver.get(CATEGORY_URL)
time.sleep(5)  # Initial full load wait

# Scroll to bottom to load all products (if lazy-loaded)
driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
time.sleep(5)

product_links = set()
elements = driver.find_elements(By.CSS_SELECTOR, 'div.product-card-grid--supplier')

for elem in elements:
    a_tag = elem.find_element(By.CSS_SELECTOR, 'a')  # find the <a>
    href = a_tag.get_attribute("href")
    if href:
        product_links.add(href)

print(f"Found {len(product_links)} product links.")

# === Step 2: Visit Each Product Link and Scrape Details ===
def scrape_product(url, retries=2):
    data = {}
    for attempt in range(retries):
        try:
            driver.get(url)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1.product-block__title")))
            break  # Success
        except:
            print(f"⚠️ Retry {attempt+1}/{retries} for URL: {url}")
            time.sleep(3)
    else:
        print(f"❌ Failed to load product page after {retries} retries: {url}")
        data["Product Name"] = "Title not found"
        data["Price"] = "Price not found"
        data["Image URLs"] = "No image gallery found"
        return data

    # Product Name
    try:
        pname_elem = driver.find_element(By.CSS_SELECTOR, "h1.product-block__title")
        data["Product Name"] = pname_elem.text.strip()
    except:
        data["Product Name"] = "Product Name not found"

    # Price
    try:
        price_elem = driver.find_element(By.CSS_SELECTOR, "div.product-block__price-new")
        data["Price"] = price_elem.text.strip()
    except:
        data["Price"] = "Price not found"

    # Force all hidden items to be displayed
    driver.execute_script("""
        document.querySelectorAll('[data-show-elements-item]').forEach(function(el) {
            el.style.display = 'block';
        });
    """)

    # Description
    try:
        description_items = driver.find_elements(By.CSS_SELECTOR, "ul.product-description__list li.product-description__item")
        for li in description_items:
            try:
                title_tag = li.find_element(By.CSS_SELECTOR, "span.product-description__item-title")
                value_tag = li.find_element(By.CSS_SELECTOR, "span.product-description__item-value")
                title = title_tag.text.strip().replace(":", "")
                value = value_tag.text.strip()

                # Force EAN numbers to be treated as text in Excel
                if "EAN" in title and value.isdigit():
                    value = f"'{value}"

                data[title] = value
            except Exception as e:
                print(f"Error parsing description item: {e}")
    except Exception as e:
        print(f"Error locating product description list: {e}")

    # --- Get Trade numbers ---
    try:
        trade_num = driver.find_element(By.CSS_SELECTOR, "div.product-block__seo-info-text")
        text = trade_num.text.strip()
        # Remove leading "Trade numbers:" if present
        if text.lower().startswith("trade numbers:"):
            text = text.split(":", 1)[1].strip()
        data["Trade numbers"] = text
    except Exception:
        data["Trade numbers"] = "Trade num not found"

     # Product URL
    data["Product URL"] = url

    # Category URL
    data["Category URL"] = CATEGORY_URL

    # Images
    image_urls = []
    try:
        img_containers = driver.find_elements(By.CSS_SELECTOR, "div.product-gallery__big-image img")
        for img in img_containers:
            src = img.get_attribute("src") or img.get_attribute("data-srcset") or img.get_attribute("srcset")
            if src:
                clean_url = src.split(",")[0].strip().split(" ")[0]
                if not clean_url.startswith("http"):
                    clean_url = BASE_URL + clean_url
                image_urls.append(clean_url)
        data["Image URLs"] = "\n".join(image_urls) if image_urls else "No images found"
    except:
        data["Image URLs"] = "No image gallery found"

    return data

# === Loop through all products and scrape ===
all_data = []
for i, link in enumerate(product_links):
    print(f"\n🔍 Scraping {i+1}/{len(product_links)}: {link}")
    try:
        product_data = scrape_product(link)
        all_data.append(product_data)

        # Print for demonstration
        for key, value in product_data.items():
            print(f"{key}: {value}")
    except Exception as e:
        print(f"❌ Error scraping product at {link}: {e}")

# === Save to CSV ===
csv_file = "brake-power-regulator.csv"
if all_data:
    # Define preferred field order
    preferred_fields = ["Product Name", "Price", "Product URL", "Image URLs", "Category URL"]

    # Collect all other fields
    all_keys = set()
    for product in all_data:
        all_keys.update(product.keys())

    remaining_fields = [field for field in all_keys if field not in preferred_fields]

    # Final fieldnames in order
    fieldnames = preferred_fields + sorted(remaining_fields)

    try:
        with open(csv_file, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for product in all_data:
                writer.writerow(product)
        print(f"\n✅ Data successfully saved to '{csv_file}' with preferred column order.")
    except Exception as e:
        print(f"\n❌ Failed to write to CSV: {e}")
else:
    print("\n⚠️ No product data found to write to CSV.")

# === Close Browser ===
driver.quit()

