from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time


def test_javascript_sites():
    # Setup options
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # Add headless back for speed
    chrome_options.add_argument("--headless")
    # Block images and CSS for speed
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")

    print("Starting Chrome browser...")
    start_time = time.time()

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )

    print(f"Browser started in {time.time() - start_time:.2f} seconds")

    # Test different sites
    test_sites = [
        "https://cnn.com",  # Simple site
        "https://rateyourmusic.com",  # Site that blocked you before
        "https://www.ebay.com"  # Another site that might have blocked you
    ]

    for url in test_sites:
        try:
            print(f"\n--- Testing {url} ---")
            start = time.time()
            driver.get(url)

            # Wait a bit for JavaScript
            time.sleep(2)

            # Get info
            print(f"Title: {driver.title}")

            # Count some elements
            links = driver.find_elements(By.TAG_NAME, "a")
            images = driver.find_elements(By.TAG_NAME, "img")

            print(f"Links found: {len(links)}")
            print(f"Images found: {len(images)}")
            print(f"Load time: {time.time() - start:.2f} seconds")

        except Exception as e:
            print(f"Error with {url}: {str(e)}")

    driver.quit()
    print("\nAll tests complete!")


if __name__ == "__main__":
    test_javascript_sites()