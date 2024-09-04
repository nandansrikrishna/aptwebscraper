import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, quote
import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

def crawl_website(base_url):
    visited_urls = set()
    to_visit = [base_url]

    # Set up Selenium with Chrome
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument("user-agent=insomnia/9.3.3")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    def is_valid_url(url):
        # Exclude URLs with fragments (anchors) and ensure it starts with the full base URL
        parsed_url = urlparse(url)
        return url.startswith(base_url) and not parsed_url.fragment

    while to_visit:
        current_url = to_visit.pop(0)
        if current_url in visited_urls:
            continue

        try:
            print(f"Crawling: {current_url}")
            driver.get(current_url)
            time.sleep(2)  # Allow time for JavaScript to execute
            
            page_source = driver.page_source
            visited_urls.add(current_url)

            # Save the response content to a file
            file_name = f"{quote(current_url, safe='')}.html"
            with open(os.path.join('crawled_pages', file_name), 'w', encoding='utf-8') as file:
                file.write(page_source)

            soup = BeautifulSoup(page_source, 'html.parser')
            # Find all links on the page
            for link in soup.find_all('a', href=True):
                new_url = urljoin(current_url, link['href'])
                if is_valid_url(new_url) and new_url not in visited_urls:
                    to_visit.append(new_url)
            
            # Be polite to the server
            time.sleep(1)

        except Exception as e:
            print(f"Error crawling {current_url}: {e}")

    driver.quit()
    return visited_urls

if __name__ == "__main__":
    base_url = "https://www.sterlinghousing.com/ann-arbor-mi/sterling-arbor-blu"
    os.makedirs('crawled_pages', exist_ok=True)
    crawled_urls = crawl_website(base_url)
    
    print(f"Crawling complete. Visited {len(crawled_urls)} unique pages.")
    for url in crawled_urls:
        print(url)

    # Optionally, save URLs to a file
    with open('crawled_urls.txt', 'w') as f:
        for url in crawled_urls:
            f.write(f"{url}\n")
