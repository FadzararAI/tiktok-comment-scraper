#!/usr/bin/env python3
"""
TikTok Comment Scraper
Extracts comments, replies, and user information from public TikTok videos.
"""

import argparse
import csv
import re
import time
import sys
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urlparse

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    import pandas as pd
except ImportError as e:
    print(f"Error: Missing required package. Please install dependencies with: pip install -r requirements.txt")
    print(f"Details: {e}")
    sys.exit(1)


class TikTokScraper:
    """TikTok comment scraper using Playwright for browser automation."""
    
    def __init__(self, url: str, output_file: str = "comments.csv", headless: bool = True):
        """
        Initialize the TikTok scraper.
        
        Args:
            url: TikTok video URL
            output_file: Output CSV filename
            headless: Run browser in headless mode
        """
        self.url = url
        self.output_file = output_file
        self.headless = headless
        self.comments = []
        
    def validate_url(self) -> bool:
        """
        Validate if the URL is a valid TikTok video URL.
        
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            parsed = urlparse(self.url)
            # Check if it's a TikTok domain
            if 'tiktok.com' not in parsed.netloc.lower():
                print(f"Error: Invalid TikTok URL. Domain must be tiktok.com")
                return False
            
            # Check if it contains /video/ or is a valid TikTok URL format
            if '/video/' not in self.url and not re.search(r'/@[\w.-]+/video/\d+', self.url):
                print(f"Error: URL doesn't appear to be a TikTok video URL")
                return False
                
            return True
        except Exception as e:
            print(f"Error validating URL: {e}")
            return False
    
    def scroll_to_load_comments(self, page, max_scrolls: int = 20):
        """
        Scroll the page to load more comments.
        
        Args:
            page: Playwright page object
            max_scrolls: Maximum number of scroll attempts
        """
        print("Loading comments (scrolling)...")
        previous_comment_count = 0
        no_change_count = 0
        
        for i in range(max_scrolls):
            # Scroll down
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)  # Wait for content to load
            
            # Check if new comments loaded
            try:
                current_comments = page.locator('[data-e2e="comment-item"]').count()
                
                if current_comments == previous_comment_count:
                    no_change_count += 1
                    if no_change_count >= 3:  # Stop if no new comments after 3 attempts
                        print(f"No more comments to load (reached end).")
                        break
                else:
                    no_change_count = 0
                    print(f"Loaded {current_comments} comments so far...")
                    
                previous_comment_count = current_comments
            except Exception as e:
                print(f"Note: Error checking comment count: {e}")
                break
        
        # Final scroll up to ensure all comments are in view
        page.evaluate("window.scrollTo(0, 0)")
        time.sleep(1)
    
    def extract_comments(self, page) -> List[Dict]:
        """
        Extract comments from the page.
        
        Args:
            page: Playwright page object
            
        Returns:
            List of comment dictionaries
        """
        comments = []
        print("Extracting comment data...")
        
        try:
            # Wait for comments to load
            page.wait_for_selector('[data-e2e="comment-item"]', timeout=10000)
            
            # Get all comment elements
            comment_elements = page.locator('[data-e2e="comment-item"]').all()
            print(f"Found {len(comment_elements)} comment elements")
            
            for idx, comment_elem in enumerate(comment_elements):
                try:
                    # Extract username
                    username = ""
                    try:
                        username_elem = comment_elem.locator('[data-e2e="comment-username"]').first
                        username = username_elem.inner_text(timeout=1000)
                    except Exception:
                        try:
                            # Alternative selector
                            username_elem = comment_elem.locator('a[href*="/@"]').first
                            username = username_elem.inner_text(timeout=1000)
                        except Exception:
                            username = "unknown"
                    
                    # Extract comment text
                    comment_text = ""
                    try:
                        text_elem = comment_elem.locator('[data-e2e="comment-level-1"], [data-e2e="comment-level-2"]').first
                        comment_text = text_elem.inner_text(timeout=1000)
                    except Exception:
                        try:
                            # Alternative: look for any text content in comment
                            spans = comment_elem.locator('span').all()
                            for span in spans:
                                text = span.inner_text(timeout=500).strip()
                                if len(text) > len(comment_text):
                                    comment_text = text
                        except Exception:
                            comment_text = ""
                    
                    # Extract likes count
                    likes = 0
                    try:
                        likes_elem = comment_elem.locator('[data-e2e="comment-like-count"]').first
                        likes_text = likes_elem.inner_text(timeout=1000)
                        # Parse likes (could be "1K", "1.2K", "1M", etc.)
                        likes = self.parse_number(likes_text)
                    except Exception:
                        likes = 0
                    
                    # Extract timestamp
                    timestamp = ""
                    try:
                        time_elem = comment_elem.locator('time, [datetime]').first
                        timestamp = time_elem.get_attribute('datetime', timeout=1000) or ""
                        if not timestamp:
                            timestamp = time_elem.inner_text(timeout=1000)
                    except Exception:
                        try:
                            # Look for relative time text like "1d ago", "2h ago"
                            text_content = comment_elem.inner_text(timeout=1000)
                            time_pattern = r'\d+[smhd]\s*ago|\d+-\d+-\d+'
                            match = re.search(time_pattern, text_content)
                            timestamp = match.group(0) if match else ""
                        except Exception:
                            timestamp = ""
                    
                    # Check if it's a reply
                    is_reply = False
                    reply_to = ""
                    try:
                        # Check for reply indicator in the comment structure
                        reply_indicator = comment_elem.locator('[data-e2e="comment-reply-to"]').first
                        is_reply = True
                        reply_to = reply_indicator.inner_text(timeout=1000)
                    except Exception:
                        # Check for indentation or nesting
                        try:
                            class_attr = comment_elem.get_attribute('class') or ""
                            if 'reply' in class_attr.lower() or 'level-2' in class_attr.lower():
                                is_reply = True
                        except Exception:
                            pass
                    
                    # Generate comment ID (using index as simple ID)
                    comment_id = f"comment_{idx + 1}"
                    
                    comment_data = {
                        'comment_id': comment_id,
                        'username': username.strip() if username else "unknown",
                        'comment_text': comment_text.strip() if comment_text else "",
                        'likes': likes,
                        'timestamp': timestamp.strip() if timestamp else "",
                        'is_reply': is_reply,
                        'reply_to': reply_to.strip() if reply_to else ""
                    }
                    
                    comments.append(comment_data)
                    
                    if (idx + 1) % 10 == 0:
                        print(f"Processed {idx + 1}/{len(comment_elements)} comments...")
                        
                except Exception as e:
                    print(f"Warning: Error extracting comment {idx + 1}: {e}")
                    continue
            
            print(f"Successfully extracted {len(comments)} comments")
            
        except PlaywrightTimeoutError:
            print("Warning: No comments found on this video (timeout waiting for comments)")
        except Exception as e:
            print(f"Error extracting comments: {e}")
        
        return comments
    
    def parse_number(self, text: str) -> int:
        """
        Parse number text that might include K, M suffixes.
        
        Args:
            text: Number string like "1.2K" or "5M"
            
        Returns:
            Parsed integer value
        """
        if not text:
            return 0
        
        text = text.strip().upper()
        multiplier = 1
        
        if 'K' in text:
            multiplier = 1000
            text = text.replace('K', '')
        elif 'M' in text:
            multiplier = 1000000
            text = text.replace('M', '')
        elif 'B' in text:
            multiplier = 1000000000
            text = text.replace('B', '')
        
        try:
            number = float(text)
            return int(number * multiplier)
        except (ValueError, TypeError):
            return 0
    
    def save_to_csv(self, comments: List[Dict]):
        """
        Save comments to CSV file.
        
        Args:
            comments: List of comment dictionaries
        """
        if not comments:
            print("No comments to save.")
            return
        
        try:
            df = pd.DataFrame(comments)
            # Reorder columns to match specification
            columns_order = ['comment_id', 'username', 'comment_text', 'likes', 'timestamp', 'is_reply', 'reply_to']
            df = df[columns_order]
            
            df.to_csv(self.output_file, index=False, encoding='utf-8', quoting=csv.QUOTE_ALL)
            print(f"\n✓ Successfully saved {len(comments)} comments to {self.output_file}")
        except Exception as e:
            print(f"Error saving to CSV: {e}")
            # Fallback to basic CSV writing
            try:
                with open(self.output_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=comments[0].keys())
                    writer.writeheader()
                    writer.writerows(comments)
                print(f"✓ Saved using fallback method to {self.output_file}")
            except Exception as e2:
                print(f"Error with fallback save: {e2}")
    
    def scrape(self) -> bool:
        """
        Main scraping method.
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.validate_url():
            return False
        
        print(f"\nStarting TikTok Comment Scraper")
        print(f"URL: {self.url}")
        print(f"Output: {self.output_file}")
        print("-" * 50)
        
        try:
            with sync_playwright() as p:
                print("Launching browser...")
                browser = p.chromium.launch(headless=self.headless)
                
                # Create context with user agent to appear more like a real browser
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    viewport={'width': 1920, 'height': 1080}
                )
                
                page = context.new_page()
                
                print(f"Loading TikTok video...")
                try:
                    page.goto(self.url, wait_until='networkidle', timeout=30000)
                except Exception as e:
                    print(f"Warning: Page load timeout, continuing anyway: {e}")
                    page.goto(self.url, timeout=30000)
                
                # Wait a bit for dynamic content
                time.sleep(3)
                
                # Check if page loaded successfully
                try:
                    # Look for video or content indicators
                    page.wait_for_selector('video, [data-e2e="browse-video"]', timeout=10000)
                    print("✓ Video page loaded successfully")
                except Exception:
                    print("Warning: Could not verify video loaded. Attempting to continue...")
                
                # Scroll to load all comments
                self.scroll_to_load_comments(page)
                
                # Extract comments
                self.comments = self.extract_comments(page)
                
                # Clean up
                browser.close()
                
                # Save to CSV
                if self.comments:
                    self.save_to_csv(self.comments)
                    return True
                else:
                    print("\nWarning: No comments were extracted. The video might have no comments or the page structure may have changed.")
                    return False
                    
        except KeyboardInterrupt:
            print("\n\nScraping interrupted by user.")
            return False
        except Exception as e:
            print(f"\nError during scraping: {e}")
            print(f"Error type: {type(e).__name__}")
            return False


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description='TikTok Comment Scraper - Extract comments from TikTok videos',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --url "https://www.tiktok.com/@username/video/1234567890"
  %(prog)s --url "https://www.tiktok.com/@user/video/123" --output my_comments.csv
  %(prog)s --url "https://www.tiktok.com/@user/video/123" --no-headless

Important Notes:
  - This scraper only works with PUBLIC TikTok videos
  - No login/authentication is required or supported
  - Please respect TikTok's Terms of Service
  - Use responsibly and avoid overwhelming servers with requests
  - Rate limiting is built-in to mimic human behavior
        """
    )
    
    parser.add_argument(
        '--url',
        required=True,
        help='TikTok video URL (e.g., https://www.tiktok.com/@username/video/1234567890)'
    )
    
    parser.add_argument(
        '--output',
        default='comments.csv',
        help='Output CSV filename (default: comments.csv)'
    )
    
    parser.add_argument(
        '--no-headless',
        action='store_true',
        help='Show browser window during scraping (useful for debugging)'
    )
    
    args = parser.parse_args()
    
    # Create scraper instance
    scraper = TikTokScraper(
        url=args.url,
        output_file=args.output,
        headless=not args.no_headless
    )
    
    # Run scraper
    success = scraper.scrape()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
