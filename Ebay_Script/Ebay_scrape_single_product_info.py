#Install List
#!pip install recipe-scrapers requests beautifulsoup4 pandas

import requests
import time
from bs4 import BeautifulSoup
import csv

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

BASE_URL = "https://www.ebay.com"
TEST_PRODUCT_URL = "https://www.ebay.com/itm/296130232994"

def scrape_product(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            print(f"Failed to fetch {url}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")

        # Collect shared product data
        base_data = {}
        product_name = soup.find("h1", class_="x-item-title__mainTitle")
        base_data["Product Name"] = product_name.get_text(strip=True) if product_name else "No product name found"

        price = soup.find("div", class_="x-price-primary")
        base_data["Price"] = price.get_text(strip=True) if price else "No price found"

        item_divs = soup.find_all("div", class_="ux-layout-section__textual-display")
        item_number = "No item number found"
        for div in item_divs:
            label = div.find("span", class_="ux-textspans ux-textspans--SECONDARY")
            value = div.find("span", class_="ux-textspans ux-textspans--BOLD")
            if label and "eBay item number" in label.get_text():
                item_number = value.get_text(strip=True) if value else "No item number found"
                break

        base_data["Item Number"] = item_number

        base_data["Product URL"] = url
        base_data["Category URL"] = TEST_PRODUCT_URL

        # Get dynamic labels and values
        sections = soup.find_all('dl', {'data-testid': 'ux-labels-values'})
        for section in sections:
            label_tags = section.find_all('dt')
            value_tags = section.find_all('dd')
            for label_tag, value_tag in zip(label_tags, value_tags):
                label = label_tag.get_text(strip=True)
                value = value_tag.get_text(strip=True)
                base_data[label] = value

        # Get product image
        image_div = soup.find("div", class_="ux-image-grid-container")
        if image_div:
            img_tag = image_div.find("img")
            if img_tag:
                image_url = img_tag.get("data-lazy-src") or img_tag.get("src")
                if image_url and not image_url.startswith("http"):
                    image_url = BASE_URL + image_url
                base_data["Image URL"] = image_url
            else:
                base_data["Image URL"] = "No image found"

        # Extract table data
        final_rows = []
        table = soup.find('table')
        if not table:
            raise Exception("No table found on the page")

        rows = table.find_all('tr')[1:]  # Skip the header
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 5:
                year = cols[0].get_text(strip=True)
                make = cols[1].get_text(strip=True)
                model = cols[2].get_text(strip=True)
                trim = cols[3].get_text(strip=True)
                engine = cols[4].get_text(strip=True)
                notes = cols[5].get_text(strip=True) if len(cols) > 5 else "Empty"

                # Merge table row with shared product data
                combined_data = base_data.copy()
                combined_data.update({
                    "Year": year,
                    "Make": make,
                    "Model": model,
                    "Trim": trim,
                    "Engine": engine,
                    "Notes": notes
                })

                final_rows.append(combined_data)

        return final_rows

    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return []

def scrape_single_product():
    print(f"Scraping product: {TEST_PRODUCT_URL}")
    product_data_list = scrape_product(TEST_PRODUCT_URL)
    if not product_data_list:
        print("Failed to scrape product data.")
        return

    print("\n🔍 Product Data Preview:")
    for item in product_data_list:
        print(item)

    # Collect all keys to form dynamic headers
    headers = set()
    for row in product_data_list:
        headers.update(row.keys())
    headers = list(headers)

    with open('test.csv', mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        writer.writerows(product_data_list)

    print("\n✅ Product data with table entries saved to 'test.csv'")

scrape_single_product()
