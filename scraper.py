import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime


def scrape(url):
    try:
        # Add timeout and headers to look more like a real browser
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        page = requests.get(url, headers=headers, timeout=10)

        # Check if request was successful
        page.raise_for_status()  # This raises an exception for bad status codes

        soup = BeautifulSoup(page.content, 'html.parser')

        data = {}

        # This scrapes the title
        data['title'] = soup.title.string.strip() if soup.title else "No Title Found"

        # This finds all meta data
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        data['meta'] = meta_desc.get('content') if meta_desc else "No Meta Found"

        # This finds the headlines
        headlines = []
        for tag in soup.find_all(['h1', 'h2', 'h3']):
            if tag.string:
                headlines.append(tag.string.strip())
        data['headlines'] = headlines

        links = []
        for link in soup.find_all('a', href=True):
            link_text = link.get_text(strip=True)  # Gets the clickable text
            link_url = link.get('href')  # Gets the URL

            if link_text and link_url:
                links.append({
                    'text': link_text,
                    'url': link_url
                })

        data['links'] = links

        stats = {}
        stats['total_elements'] = len(soup.find_all())  # Count all HTML elements
        stats['total_links'] = len(links)  # Number of links we found
        stats['total_images'] = len(soup.find_all('img'))  # Count all images
        stats['page_size'] = round(len(page.content) / 1024, 1)  # Page size in KB

        data['stats'] = stats

        # This saves our data
        save_to_csv(data, url)

        return data

    except requests.exceptions.RequestException as e:
        return f"Error scraping {url}: {str(e)}"


def save_to_csv(data, url):
    filename = "scraped_data.csv"

    try:
        # Check if this is the first time writing to the file
        try:
            with open(filename, 'x', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                # Write the header row (column names)
                writer.writerow(
                    ['timestamp', 'url', 'title', 'meta_description', 'num_headlines', 'num_links', 'total_elements',
                     'total_images', 'page_size_kb'])
                print(f"Created new CSV file: {filename}")
        except FileExistsError:
            print(f"CSV file {filename} already exists")

        # Add the new data
        with open(filename, 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            row_data = [
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                url,
                data.get('title', ''),
                data.get('meta', ''),
                len(data.get('headlines', [])),
                len(data.get('links', [])),
                data.get('stats', {}).get('total_elements', 0),
                data.get('stats', {}).get('total_images', 0),
                data.get('stats', {}).get('page_size', 0)
            ]
            writer.writerow(row_data)
            print(f"Added data to CSV: {url}")

    except Exception as e:
        print(f"Error saving to CSV: {e}")