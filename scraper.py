import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, quote
import time
import os
import re
import string
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from supabase import create_client, Client

url = "https://tkweddqlriikqgylsuxz.supabase.co"
service_role_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRrd2VkZHFscmlpa3FneWxzdXh6Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTY3MjA3NzQyMiwiZXhwIjoxOTg3NjUzNDIyfQ.p2Lzfx1wE7f2H25xu1TjfnP43avSZWHrrGoN__ChIZ8"
supabase: Client = create_client(url, service_role_key)

def is_valid_url(url):
    # Exclude URLs with fragments (anchors), ensure it starts with the full base URL,
    # and allow URLs that end with .html or with a slash
    parsed_url = urlparse(url)
    path = parsed_url.path.lower()  # Convert path to lowercase for case-insensitive matching

    # Check if the URL ends with a slash or .html
    is_valid_extension = path.endswith('/') or path.endswith('.html')

    # List of keywords to exclude (privacy policy, terms of service, accessibility)
    exclusion_keywords = ['privacy', 'policy', 'terms', 'service', 'accessibility', 'cookies', 'legal']

    # Check if the URL contains any exclusion keywords
    contains_exclusion_keyword = any(keyword in path for keyword in exclusion_keywords)

    return (
        url.startswith(base_url) and
        not parsed_url.fragment and
        is_valid_extension and
        not contains_exclusion_keyword
    )

def is_standard_url(src):
    # Check if the src is a standard URL (starting with http or https)
    return src.startswith('http://') or src.startswith('https://')

# Dictionary to keep track of whether each tag has been saved
saved_tags = {'header': False, 'nav': False, 'footer': False}

def save_tag_content(tag, tag_name, base_url):
    if tag:
        os.makedirs('tags', exist_ok=True)  # Ensure the 'tags' folder exists

        preprocessed_content = preprocess_text(tag.get_text(separator='\n').strip())

        file_name = f"{tag_name}_{quote(base_url, safe='')}.txt"
        with open(os.path.join('tags', file_name), 'w', encoding='utf-8') as file:
            file.write(preprocessed_content)

def get_high_quality_image(src):
    # return re.sub(r'-\d+x\d+', '', src)
    return src

def preprocess_text(text):
    # Convert text to lowercase
    text = text.lower()
    
    # Remove punctuation, but preserve newlines
    text = re.sub(f"[{re.escape(string.punctuation)}]", "", text)
    
    # Normalize spaces, but preserve newlines
    text = re.sub(r'[ \t]+', ' ', text)  # Replace spaces and tabs with a single space
    
    # Remove any blank lines (consecutive newlines)
    text = re.sub(r'\n\s*\n+', '\n', text)

    return text

def crawl_website(base_url):
    visited_urls = set()
    to_visit = [base_url]
    collected_img_sources = set()

    # Set up Selenium with Chrome
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument("user-agent=insomnia/9.3.3")
    
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

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

            soup = BeautifulSoup(page_source, 'html.parser')

            # Find all links on the page
            for link in soup.find_all('a', href=True):
                new_url = urljoin(current_url, link['href'])
                # TODO: Run LLM on url to check if its a privacy policy or other such irrelevant link
                if is_valid_url(new_url) and new_url not in visited_urls:
                    to_visit.append(new_url)

            # TODO: Find primary color of company
            # Use apply button color as primary

            # Extract and save the first encountered header, nav, and footer tags
            tags_to_save = ['header', 'nav', 'footer']
            for tag_name in tags_to_save:
                tag = soup.find(tag_name)
                if tag and not saved_tags[tag_name]:  # Check if the tag hasn't been saved yet
                    save_tag_content(tag, tag_name, base_url)
                    saved_tags[tag_name] = True  # Mark the tag as saved
                if tag:
                    tag.decompose()  # Remove the tag from the soup, regardless of whether it was saved

            
            img_sources = []
            for img in soup.find_all('img'):
                if img.get('srcset'):
                    # Get the highest quality image from srcset
                    high_quality_image = img['srcset'].split(',')[-1].strip().split(' ')[0]
                    img_sources.append(high_quality_image)
                elif img.get('data-src'):
                    # Handle lazy-loaded images
                    # TODO: get_high_quality_image here
                    img_sources.append(img['data-src'])
                else:
                    # TODO: get_high_quality_image here
                    img_sources.append(img['src'])

            img_sources = [urljoin(base_url, src) for src in img_sources if is_standard_url(src)]
            for src in img_sources:
                if src not in collected_img_sources:
                    collected_img_sources.add(src)
                    with open('image_sources.txt', 'a') as f:
                        f.write(src + '\n')
            
            # TODO: Find json responses in network requests for additonal data

            # Get all text content and strip out all HTML markup
            text_content = re.sub(r'\n+', '\n', soup.get_text(separator='\n').strip())

            # Preprocess the text: lowercase, remove punctuation, normalize whitespace
            preprocessed_text = preprocess_text(text_content)

            # Save the plain, preprocessed text content to a file
            file_name = f"{quote(current_url, safe='')}.txt"
            with open(os.path.join('crawled_pages', file_name), 'w', encoding='utf-8') as file:
                file.write(preprocessed_text)

        except Exception as e:
            print(f"Error crawling {current_url}: {e}")

    driver.quit()
    return visited_urls

def read_text_files_from_directory(directory):
    combined_text = []
    for filename in os.listdir(directory):
        if filename.endswith('.txt'):
            with open(os.path.join(directory, filename), 'r', encoding='utf-8') as file:
                text = file.read()
                combined_text.append(text)
    return combined_text

def create_raw_corpus(crawled_pages_dir, tags_dir):
    # Read and combine text from both directories
    tags_text = read_text_files_from_directory(tags_dir)
    crawled_pages_text = read_text_files_from_directory(crawled_pages_dir)
    
    # Combine all the text into a single corpus
    combined_corpus = '\n'.join(tags_text + crawled_pages_text)
    
    # Remove duplicate lines
    seen_lines = set()
    final_corpus_lines = []
    for line in combined_corpus.splitlines(keepends=True):
        if line not in seen_lines:
            final_corpus_lines.append(line)
            seen_lines.add(line)
    
    # Combine the deduplicated lines into the final corpus
    final_corpus = ''.join(final_corpus_lines)
    
    return final_corpus

def refine_4o(prompt):
    # Define the URL
    url = "https://tour.video/api/ai/completion"

    # Define the request body
    data = {
        "prompt": prompt
    }

    return requests.post(url, json=data)

def save_corpus_to_file(corpus, output_file):
    with open(output_file, 'w', encoding='utf-8') as file:
        file.write(corpus)

# Update the `ai` column in the `community` table
def update_ai_column(community_id, new_value):
    response = supabase.table("Community").update({"ai": new_value}).eq("id", community_id).execute()
    return response

if __name__ == "__main__":
    base_url = "https://bankierapartments.com/"
    os.makedirs('crawled_pages', exist_ok=True)
    crawled_urls = crawl_website(base_url)
    
    print(f"Crawling complete. Visited {len(crawled_urls)} unique pages.")
    for url in crawled_urls:
        print(url)

    crawled_pages_dir = 'crawled_pages'
    tags_dir = 'tags'

    raw_corpus = create_raw_corpus(crawled_pages_dir, tags_dir)
    
    # save_corpus_to_file(raw_corpus, "raw.txt")

    prompt = "Strip all unnecessary text that doesnt give useful information for this apartment property. Return only plain text. Simply remove unnecessary lines. Make sure to include all relevant detail from the initial text:\n"

    refined_text = refine_4o(prompt + raw_corpus).text

    # save_corpus_to_file(refined_text, "refined.txt")

    community_id = 5
    new_ai_value = json.loads(refined_text)["response"]

    dic = {"corpus" : new_ai_value}

    response = update_ai_column(community_id, dic)
    print(response)

    # # Optionally, save URLs to a file
    # with open('crawled_urls.txt', 'w') as f:
    #     for url in crawled_urls:
    #         f.write(f"{url}\n")
