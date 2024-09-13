from local_scraper import run_scraper
import time
import os
from supabase import create_client, Client

# Supabase setup
url = os.environ.get('SUPABASE_URL')
service_role_key = os.environ.get('SUPABASE_KEY')
supabase: Client = create_client(url, service_role_key)

def fetch_communities_with_empty_ai():
    try:
        response = supabase.table("Community").select("id", "url", "ai").is_("ai", "null").execute()
        return response.data
    except Exception as e:
        print(f"Error fetching communities: {str(e)}")
        return []

def main():
    communities = fetch_communities_with_empty_ai()
    
    if not communities:
        print("No communities found with empty AI column or error occurred while fetching communities.")
        return

    print(f"Found {len(communities)} communities with empty AI column. Starting scraping process...")

    for community in communities:
        community_id = community['id']
        url = community['url']
        
        if not url:
            print(f"Skipping community {community_id}: No URL provided")
            continue

        print(f"Processing community {community_id} with URL: {url}")
        
        result = run_scraper(url, community_id)
        
        if result:
            print(f"Scraping completed successfully for community {community_id}")
        else:
            print(f"Scraping failed for community {community_id}")
        
        # Add a small delay to avoid overloading the server
        time.sleep(2)

    print("Scraping process completed for all communities with empty AI column.")

if __name__ == "__main__":
    main()