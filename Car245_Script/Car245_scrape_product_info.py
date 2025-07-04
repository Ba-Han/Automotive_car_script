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
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import csv
import time
import re

# Configuration
BASE_URL = "https://cars245.com"
CATEGORY_URL = "https://cars245.com/en/catalog/5422.suspension-damping/"

# Set up Selenium WebDriver
options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

def get_product_links(driver):
    product_links = []
    for page in range(1, 16):  # Stop at page 15
        url = f"{CATEGORY_URL}?page={page}"
        print(f"Scraping category page: {url}")
        driver.get(url)

        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "product-card"))
            )
        except Exception:
            print("No more products or failed to load.")
            break

        soup = BeautifulSoup(driver.page_source, "html.parser")
        product_items = soup.find_all("a", class_="product-card")

        if not product_items:
            print("No products found on this page.")
            break

        for item in product_items:
            product_links.append(BASE_URL + item.get("href"))

        time.sleep(1)  # Be polite

    return product_links

def scrape_product_selenium(driver, url):
    driver.get(url)
    time.sleep(3)  # Wait for JavaScript to load content

    soup = BeautifulSoup(driver.page_source, "html.parser")

    product_name = soup.find("h1", class_="h1")
    product_name = product_name.get_text(strip=True) if product_name else "No product name found"

    product_number = soup.find("h4", class_="h4")
    product_number = product_number.get_text(strip=True) if product_number else "No product number found"

    price = soup.find("div", class_="price")
    price = price.get_text(strip=True) if price else "No price found"

    manufacturer = soup.find("a", class_="unit-product__supplier-label-link")
    manufacturer_supplier = manufacturer.get_text(strip=True) if price else "No manufacturer"

    product_data = {
        "Product Name": product_name,
        "Product Number": product_number,
        "Price": price,
        "Product URL": url,
        "Category URL": CATEGORY_URL,
        "Manufacturer Supplier": manufacturer_supplier
    }

    product_info_div = soup.find("div", class_="unit-product__details-list")
    if product_info_div:
        last_key = None
        for item in product_info_div.find_all("div", class_="striped-list__row"):
            key_element = item.find("div", class_="striped-list__left --add-bold")
            value_element = item.find("div", class_="striped-list__right")

            if value_element:
                key_text = key_element.get_text(strip=True) if key_element else ""
                value = value_element.get_text(strip=True)

                if key_text:  # New key
                    key = key_text.replace(":", "")
                    last_key = key
                elif last_key:
                    key = last_key
                else:
                    continue

                if "ean" in key.lower() and value.isdigit():
                    value = f"'{value}"
                elif "item number" in key.lower() and value.isdigit():
                    value = f"'{value}"

                # Combine multiple values into one, line-separated
                if key in product_data:
                    product_data[key] += f"\n{value}"
                else:
                    product_data[key] = value

    image_div = soup.find("div", class_="unit-product__pictures")
    if image_div:
        img_tag = image_div.find("img")
        if img_tag:
            image_url = img_tag.get("data-lazy-src") or img_tag.get("src")
            if image_url and not image_url.startswith("http"):
                image_url = BASE_URL + image_url
            product_data["Image URL"] = image_url
        else:
            product_data["Image URL"] = "No image found"

    return product_data, soup

# def scrape_table_data(soup):
#     oem_data = []
#     vehicle_data = []
#     ...
#     return oem_data, vehicle_data

def scrape_all_product():
    product_links = get_product_links(driver)

    if not product_links:
        print("No product links found.")
        driver.quit()
        return

    output_file = "suspension-damping.csv"

    all_rows = []

    # --- Fixed headers always shown first ---
    fixed_headers = ["Product Name", "Product Number", "Price", "Product URL", "Category URL", "Image URL", "Manufacturer Supplier"]
    all_detected_headers = set(fixed_headers)  # To collect dynamic headers

    # Commented: OEM and vehicle headers
    # oem_headers = ["OEM Brand", "OEM Code", "OEM Quality", "OEM Product", "OEM Price"]
    # vehicle_headers = ["VC Model", "VC Engine Code", "VC Fuel", "VC Displacement", "VC HP", "VC KW", "VC Year"]

    for index, url in enumerate(product_links, start=1):
        print(f"\nScraping product {index}/{len(product_links)}: {url}")
        try:
            product_data, soup = scrape_product_selenium(driver, url)

            # Commented: OEM and vehicle scraping
            # oem_data, vehicle_data = scrape_table_data(soup)

            all_detected_headers.update(product_data.keys())

            row_dict = {}
            for key in all_detected_headers:
                row_dict[key] = product_data.get(key, "")
            all_rows.append(row_dict)

            # Commented: multiple rows with oem_data and vehicle_data
            # if not oem_data:
            #     oem_data = [[""] * len(oem_headers)]
            # if not vehicle_data:
            #     vehicle_data = [[""] * len(vehicle_headers)]

            # first_row = True
            # for oem_row in oem_data:
            #     for vehicle_row in vehicle_data:
            #         row_dict = {}
            #         if first_row:
            #             for key in all_detected_headers:
            #                 row_dict[key] = product_data.get(key, "")
            #             first_row = False
            #         else:
            #             for key in all_detected_headers:
            #                 row_dict[key] = ""
            #         for i, key in enumerate(oem_headers):
            #             row_dict[key] = oem_row[i] if i < len(oem_row) else ""
            #         for i, key in enumerate(vehicle_headers):
            #             row_dict[key] = vehicle_row[i] if i < len(vehicle_row) else ""
            #         all_rows.append(row_dict)

        except Exception as e:
            print(f"❌ Error scraping {url}: {e}")
            continue

    driver.quit()

    # --- Order headers ---
    dynamic_spec_headers = sorted(list(all_detected_headers - set(fixed_headers)))

    # Final headers now only include product fields (OEM and Vehicle fields removed)
    final_headers = fixed_headers + dynamic_spec_headers

    # --- Write to CSV ---
    with open(output_file, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=final_headers)
        writer.writeheader()
        for row in all_rows:
            writer.writerow(row)

    print(f"\n✅ All product data saved to '{output_file}'")

# Run the scraper
scrape_all_product()
