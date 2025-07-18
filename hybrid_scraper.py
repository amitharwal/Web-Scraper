import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import csv
from datetime import datetime
import time

# This is what runs when someone wants to scrape their website.
def regular_scrape(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

        session = requests.Session()
        page = session.get(url, headers=headers, timeout=10)
        page.raise_for_status()

        # If the scrape works, it will begin at this point.
        soup = BeautifulSoup(page.content, 'html.parser')
        return extract_data(soup, url, page, method="regular")

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            return "403_ERROR"
        elif e.response.status_code == 404:
            return f"Error: Page not found (404)"
        else:
            return f"HTTP_ERROR_{e.response.status_code}"
    except Exception as e:
        return f"ERROR: {type(e).__name__}"


# If something is blocked by our original scraper, it will try Selenium here.
def selenium_scrape(url):
    print(f"Regular scraper blocked, trying advanced mode...")

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")

    driver = None
    try:
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )

        driver.get(url)
        time.sleep(3)  # Wait for JavaScript to load

        # Check if we hit a challenge page
        if "Just a moment" in driver.title or "Cloudflare" in driver.page_source:
            return "CLOUDFLARE_BLOCK"

        # Create a BeautifulSoup object from Selenium's page source
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Create a fake page object to match regular scraper
        class FakePage:
            def __init__(self, content):
                self.content = content.encode('utf-8')

        fake_page = FakePage(driver.page_source)
        return extract_data(soup, url, fake_page, method="selenium")

    except Exception as e:
        return f"SELENIUM_ERROR: {str(e)}"
    finally:
        if driver:
            driver.quit()

# Extract data from soup (used by both scrapers)
def extract_data(soup, url, page, method="regular"):
    data = {}

    # Add which method was used
    data['method'] = method

    # Extract title
    data['title'] = soup.title.string.strip() if soup.title else "No Title Found"

    # Extract meta description
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    data['meta'] = meta_desc.get('content') if meta_desc else "No Meta Found"

    # Extract headlines
    headlines = []
    for tag in soup.find_all(['h1', 'h2', 'h3']):
        text = tag.get_text(strip=True)
        if text:
            headlines.append(text)
    data['headlines'] = headlines[:20]  # Limit to 20

    # Extract links
    links = []
    for link in soup.find_all('a', href=True):
        link_text = link.get_text(strip=True)
        link_url = link.get('href')

        if link_text and link_url and not link_url.startswith('#'):
            links.append({
                'text': link_text[:50],  # Limit text length
                'url': link_url[:200]  # Limit URL length
            })
    data['links'] = links[:50]  # Limit to 50 links

    # Calculate stats
    stats = {}
    stats['total_elements'] = len(soup.find_all())
    stats['total_links'] = len(links)
    stats['total_images'] = len(soup.find_all('img'))
    stats['page_size'] = round(len(page.content) / 1024, 1)
    data['stats'] = stats

    return data

# Main function that tries regular first, then Selenium if needed
def smart_scrape(url):
    print(f"\nScraping: {url}")
    print("Trying fast mode first...")

    # Try regular scraper first
    start_time = time.time()
    result = regular_scrape(url)

    # Check if we need to use Selenium
    if isinstance(result, str) and any(error in result for error in ["403_ERROR", "ERROR", "HTTP_ERROR"]):
        print(f"Fast mode failed: {result}")
        result = selenium_scrape(url)

        # Check if Selenium also failed
        if isinstance(result, str) and "ERROR" in result:
            if "CLOUDFLARE_BLOCK" in result:
                return "Error: This website has advanced bot protection that blocks all automated access."
            else:
                return f"Error: Unable to scrape this website. {result}"

    # If result is still a string, it's an error
    if isinstance(result, str):
        return result

    # Add timing info
    result['scrape_time'] = round(time.time() - start_time, 2)

    # Save to CSV
    save_to_csv(result, url)

    print(f"Success using {result['method']} method! Time: {result['scrape_time']}s")
    return result


def save_to_csv(data, url):
    filename = "scraped_data.csv"

    try:
        # Check if file exists
        try:
            with open(filename, 'x', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow([
                    'timestamp', 'url', 'title', 'meta_description',
                    'num_headlines', 'num_links', 'total_elements',
                    'total_images', 'page_size_kb', 'scrape_method', 'scrape_time'
                ])
        except FileExistsError:
            pass

        # Add data
        with open(filename, 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                url,
                data.get('title', '')[:200],
                data.get('meta', '')[:500],
                len(data.get('headlines', [])),
                len(data.get('links', [])),
                data.get('stats', {}).get('total_elements', 0),
                data.get('stats', {}).get('total_images', 0),
                data.get('stats', {}).get('page_size', 0),
                data.get('method', 'unknown'),
                data.get('scrape_time', 0)
            ])

    except Exception as e:
        print(f"Error saving to CSV: {e}")


# This is my testing function to try the hybrid scraper. Not applicable in main web service.
if __name__ == "__main__":
    test_urls = [
        "https://example.com",
        "https://example.com",
        "https://example.com"
    ]

    for url in test_urls:
        result = smart_scrape(url)
        if isinstance(result, dict):
            print(f"✓ Scraped: {result['title'][:50]}...")
        else:
            print(f"✗ Failed: {result}")
        print("-" * 50)