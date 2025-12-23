import requests
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Create a session with SSL verification disabled
session = requests.Session()
session.verify = False
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
})

def scrape_reddit(movie):
    """Scrape Reddit for movie recommendations"""
    results = []
    seen_urls = set()  # Track seen URLs to avoid duplicates
    search_url = f"https://www.reddit.com/search/?q={movie}+recommendation"
    print("Reddit search URL:", search_url)  # Debug log
    try:
        res = session.get(search_url, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        
        # Try multiple selectors for Reddit's dynamic content
        posts = (soup.select("a[data-click-id='body']") or 
                soup.select("a[href^='/r/']") or
                soup.select("a[href*='comments/']") or
                soup.select("a[href*='reddit.com/r/']"))
        print("Reddit posts", posts)  # Debug log
        for post in posts:
            try:
                title = post.get_text(strip=True)
                url = post["href"]
                if not url.startswith('http'):
                    url = f"https://www.reddit.com{url}"
                
                # Skip if we've seen this URL before
                if url in seen_urls:
                    continue
                    
                seen_urls.add(url)
                
                if movie.lower() in title.lower():
                    results.append({
                        "platform": "Reddit",
                        "source": title[:80],
                        "url": url
                    })
                    # Limit to 3 results from Reddit
                    if len(results) >= 3:
                        break
            except Exception:
                continue
                
    except Exception as e:
        print(f"Error scraping Reddit: {e}")
    
    print("Reddit scrape Response:", results)  # Debug log
    return results

def scrape_quora(movie):
    """Scrape Quora for movie recommendations"""
    results = []
    search_url = f"https://www.quora.com/search?q={movie}%20movie%20recommendation"

    try:
        # Add headers to make the request look like it's coming from a browser
        headers = {
            **session.headers,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        
        res = session.get(search_url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        
        # Try multiple selectors for Quora's dynamic content
        links = (soup.select("a[href*='/question/']") or
                soup.select("a[href*='quora.com/']") or
                soup.select("a.q-box") or
                soup.select("a.question_link") or
                soup.select("a[class*='question']"))
        
        for a in links:
            try:
                text = a.get_text(strip=True)
                href = a.get("href", "")
                
                if not href or not text or len(text) < 10:  # Skip very short texts
                    continue
                    
                if not href.startswith('http'):
                    href = f"https://www.quora.com{href}"
                
                # Clean up the URL
                href = href.split('?')[0]  # Remove query parameters
                href = href.rstrip('/')    # Remove trailing slashes
                
                if movie.lower() in text.lower() and "quora.com" in href:
                    results.append({
                        "platform": "Quora",
                        "source": text[:80],
                        "url": href
                    })
                    # Limit to 3 results from Quora
                    if len(results) >= 3:
                        break
            except Exception as e:
                continue
                
    except Exception as e:
        print(f"Error scraping Quora: {e}")
        
    return results

def scrape_youtube(movie, api_key):
    """Search YouTube for movie recommendations using YouTube Data API"""
    results = []
    
    try:
        youtube = build("youtube", "v3", developerKey=api_key)

        request = youtube.search().list(
            q=f"{movie} movie recommendation",
            part="snippet",
            maxResults=5,
            type="video"
        )

        response = request.execute()

        for item in response["items"]:
            results.append({
                "platform": "YouTube",
                "source": item["snippet"]["title"][:80],
                "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}"
            })
    except Exception as e:
        print(f"Error searching YouTube: {e}")
        
    return results

def fetch_references(movie, youtube_api_key=None):
    """
    Fetch movie recommendations from multiple platforms
    
    Args:
        movie: Movie title to search for
        youtube_api_key: YouTube Data API key (optional)
    """
    refs = []
    
    # Get Reddit recommendations
    refs.extend(scrape_reddit(movie))
    
    # Get Quora recommendations
    refs.extend(scrape_quora(movie))
    
    # Get YouTube recommendations if API key is provided
    if youtube_api_key:
        refs.extend(scrape_youtube(movie, youtube_api_key))
    
    return refs
