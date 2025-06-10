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
import pandas as pd

# Configuration
BASE_URL = "https://cars245.com"
CATEGORY_URL = "https://cars245.com/en/catalog/3318.engine/"

# Set up Selenium WebDriver
options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

def get_product_links(driver):
    product_links = []
    for page in range(1, 16):  # Stop at page 20
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
    product_data = {}

    product_info_div = soup.find("div", class_="unit-product__details-list")
    if product_info_div:
        for item in product_info_div.find_all("div", class_="striped-list__row"):
            key_element = item.find("div", class_="striped-list__left --add-bold")
            value_element = item.find("div", class_="striped-list__right")
            if key_element and value_element:
                key = key_element.get_text(strip=True).replace(":", "")
                value = value_element.get_text(strip=True)

                if "item number" in key.lower() and value.isdigit():
                    value = f"'{value}"
                product_data[key] = value

    return product_data, soup

def scrape_table_data(soup):
    oem_data = []
    vehicle_data = []

    # ✅ OEM table (traditional HTML table)
    oem_table = soup.find("table", class_="table-alternate-products")
    if oem_table:
        oem_rows = oem_table.find_all("tr")
        for row in oem_rows:
            tds = row.find_all("td")
            if not tds:
                continue
            brand = tds[0].get_text(strip=True) if len(tds) > 0 else ""
            code = tds[1].get_text(strip=True) if len(tds) > 1 else ""
            if code.isdigit():
                code = f"'{code}"
            quality = ""
            if len(tds) > 2:
                quality_span = tds[2].find("span")
                quality = quality_span.get_text(strip=True) if quality_span else tds[2].get_text(strip=True)
            product = tds[3].get_text(strip=True) if len(tds) > 3 else ""
            price = ""
            if len(tds) > 4:
                price_div = tds[4].find("div", class_="price")
                if price_div:
                    price_main = price_div.contents[0].strip() if price_div.contents else ""
                    price_decimal = ""
                    if len(price_div.contents) > 1:
                        small_tag = price_div.find("span", class_="small")
                        if small_tag:
                            price_decimal = small_tag.get_text(strip=True)
                    price = price_main + price_decimal
                else:
                    price = tds[4].get_text(strip=True)
            oem_data.append([brand, code, quality, product, price])

    # Find all model rows (each model is inside a div.simple-table__row with data-js-click-event attribute)
    model_rows = soup.find_all("div", class_="simple-table__row", attrs={"data-js-click-event": "clickCompatibilityModelRow"})

    for model_row in model_rows:
        # Extract the model name text inside span.simple-table__text
        model_name_tag = model_row.find("span", class_="simple-table__text")
        if not model_name_tag:
            continue
        model_name = model_name_tag.get_text(strip=True)

        # The next sibling row contains the tiny-table with detailed specs
        next_row = model_row.find_next_sibling("div", class_="simple-table__row")
        if not next_row:
            continue

        # Inside next_row, find the header row and data rows of tiny-table
        header_row = next_row.find("div", class_="tiny-table__row -th-row")
        data_rows = next_row.find_all("div", class_="tiny-table__row")
        if not header_row or len(data_rows) < 2:
            continue

        headers = [div.get_text(strip=True).lower() for div in header_row.find_all("div", class_="tiny-table__text")]

        # Parse each data row after header
        for row in data_rows[1:]:
            values = [div.get_text(strip=True) for div in row.find_all("div", class_="tiny-table__text")]
            while len(values) < len(headers):
                values.append("")
            vehicle_entry = dict(zip(headers, values))
            vehicle_entry["model"] = model_name  # add model explicitly

            ordered_row = [
                vehicle_entry.get("model", ""),
                vehicle_entry.get("engine code", ""),
                vehicle_entry.get("fuel", ""),
                vehicle_entry.get("displacement", ""),
                vehicle_entry.get("hp", ""),
                vehicle_entry.get("kw", ""),
                vehicle_entry.get("year", "")
            ]
            vehicle_data.append(ordered_row)


    return oem_data, vehicle_data

def scrape_all_product():
    product_links = get_product_links(driver)

    if not product_links:
        print("No product links found.")
        driver.quit()
        return

    output_file = "engine-item.csv"

    all_rows = []

    # --- Fixed headers always shown first ---
    fixed_headers = ["Item Number"]
    all_detected_headers = set(fixed_headers)  # To collect dynamic headers
    oem_headers = ["OEM Brand", "OEM Code", "OEM Quality", "OEM Product", "OEM Price"]
    vehicle_headers = ["VC Model", "VC Engine Code", "VC Fuel", "VC Displacement", "VC HP", "VC KW", "VC Year"]

    for index, url in enumerate(product_links, start=1):
      print(f"\nScraping product {index}/{len(product_links)}: {url}")
      try:
          product_data, soup = scrape_product_selenium(driver, url)
          oem_data, vehicle_data = scrape_table_data(soup)

           # Filter product_data to keep only allowed keys
          product_data = {k: v for k, v in product_data.items() if k in all_detected_headers}

          # Add Item Number to product_data for output convenience
          product_data["Item Number"] = product_data.get("Item Number", "")

          # ensure oem_data and vehicle_data rows
          if not oem_data:
              oem_data = [[""] * len(oem_headers)]
          if not vehicle_data:
              vehicle_data = [[""] * len(vehicle_headers)]

          for oem_row in oem_data:
              for vehicle_row in vehicle_data:
                  row_dict = {}

                  # Always include fixed fields like Item Number
                  for key in fixed_headers:
                      row_dict[key] = product_data.get(key, "")

                  # OEM fields
                  for i, key in enumerate(oem_headers):
                      row_dict[key] = oem_row[i] if i < len(oem_row) else ""

                  # Vehicle fields
                  for i, key in enumerate(vehicle_headers):
                      row_dict[key] = vehicle_row[i] if i < len(vehicle_row) else ""

                  all_rows.append(row_dict)

      except Exception as e:
          print(f"❌ Error scraping {url}: {e}")
          continue

    driver.quit()

    # --- Order headers ---
    final_headers = fixed_headers +  oem_headers + vehicle_headers

    # --- Write to CSV ---
    with open(output_file, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=final_headers)
        writer.writeheader()
        for row in all_rows:
            writer.writerow(row)

    print(f"\n✅ All product data saved to '{output_file}'")

# Run the scraper
scrape_all_product()