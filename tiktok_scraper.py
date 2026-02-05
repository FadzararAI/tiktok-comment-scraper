#!/usr/bin/env python3
"""
TikTok Comment Scraper
Extracts comments, replies, and user information from public TikTok videos.
"""

import argparse
import csv
import json
import random
import re
import time
import sys
from datetime import datetime
from pathlib import Path
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
    
    def __init__(self, url: str, output_file: str = "comments.csv", headless: bool = False, use_session: bool = False):
        """
        Initialize the TikTok scraper.
        
        Args:
            url: TikTok video URL
            output_file: Output CSV filename
            headless: Run browser in headless mode (default: False for CAPTCHA solving)
            use_session: Load saved browser session to avoid CAPTCHA
        """
        self.url = url
        self.output_file = output_file
        self.headless = headless
        self.use_session = use_session
        self.comments = []
        self.sessions_dir = Path("sessions")
        self.session_file = self.sessions_dir / "tiktok_session.json"
        
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
    
    def save_session(self, context):
        """
        Save browser session (cookies and localStorage) to file.
        
        Args:
            context: Playwright browser context
        """
        try:
            self.sessions_dir.mkdir(exist_ok=True)
            
            # Get cookies
            cookies = context.cookies()
            
            # Get localStorage from a page
            pages = context.pages
            local_storage = {}
            if pages:
                try:
                    local_storage = pages[0].evaluate("() => Object.assign({}, window.localStorage)")
                except Exception:
                    pass
            
            session_data = {
                'cookies': cookies,
                'local_storage': local_storage,
                'timestamp': datetime.now().isoformat()
            }
            
            with open(self.session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
            
            print(f"✓ Session saved to {self.session_file}")
        except Exception as e:
            print(f"Warning: Could not save session: {e}")
    
    def load_session(self, context):
        """
        Load browser session from file.
        
        Args:
            context: Playwright browser context
            
        Returns:
            bool: True if session loaded successfully
        """
        try:
            if not self.session_file.exists():
                print(f"No saved session found at {self.session_file}")
                return False
            
            with open(self.session_file, 'r') as f:
                session_data = json.load(f)
            
            # Add cookies
            if 'cookies' in session_data:
                context.add_cookies(session_data['cookies'])
                print(f"✓ Loaded {len(session_data['cookies'])} cookies from session")
            
            # Note: localStorage needs to be set on a page, we'll do this after navigation
            self.session_local_storage = session_data.get('local_storage', {})
            
            session_age = datetime.now() - datetime.fromisoformat(session_data.get('timestamp', datetime.now().isoformat()))
            print(f"✓ Session age: {session_age.days} days")
            
            return True
        except Exception as e:
            print(f"Warning: Could not load session: {e}")
            return False
    
    def apply_local_storage(self, page):
        """
        Apply saved localStorage to a page.
        
        Args:
            page: Playwright page object
        """
        if hasattr(self, 'session_local_storage') and self.session_local_storage:
            try:
                for key, value in self.session_local_storage.items():
                    page.evaluate(f"({{key, value}}) => window.localStorage.setItem(key, value)", 
                                  {'key': key, 'value': value})
                print(f"✓ Applied {len(self.session_local_storage)} localStorage items")
            except Exception as e:
                print(f"Warning: Could not apply localStorage: {e}")
    
    def detect_captcha(self, page) -> bool:
        """
        Detect if CAPTCHA is present on the page.
        
        Args:
            page: Playwright page object
            
        Returns:
            bool: True if CAPTCHA detected
        """
        try:
            # Common CAPTCHA indicators for TikTok
            captcha_selectors = [
                'iframe[src*="captcha"]',
                '[id*="captcha"]',
                '[class*="captcha"]',
                'div[id*="verify"]',
                'div[class*="verify"]',
                'div[class*="Verify"]',
                '[data-e2e="captcha"]',
                '.verify-container',
                '#verify-container',
                '.secsdk-captcha',
                '.captcha_verify_container'
            ]
            
            for selector in captcha_selectors:
                try:
                    element = page.locator(selector).first
                    if element.count() > 0:
                        return True
                except Exception:
                    continue
            
            # Check page content for CAPTCHA text
            try:
                page_text = page.content()
                captcha_keywords = ['verify', 'captcha', 'robot', 'verification', 'puzzle', 'challenge']
                page_text_lower = page_text.lower()
                
                # Only flag if multiple keywords are present
                keyword_count = sum(1 for keyword in captcha_keywords if keyword in page_text_lower)
                if keyword_count >= 2:
                    return True
            except Exception:
                pass
            
            return False
        except Exception as e:
            print(f"Warning: Error detecting CAPTCHA: {e}")
            return False
    
    def wait_for_captcha_solve(self, page, timeout: int = 300):
        """
        Wait for user to solve CAPTCHA manually.
        
        Args:
            page: Playwright page object
            timeout: Maximum wait time in seconds (default: 5 minutes)
            
        Returns:
            bool: True if CAPTCHA solved, False if timeout
        """
        print("\n" + "=" * 60)
        print("⚠️  CAPTCHA DETECTED!")
        print("=" * 60)
        print("Please solve the CAPTCHA in the browser window.")
        print("The scraper will automatically continue once solved.")
        print(f"Timeout: {timeout} seconds ({timeout//60} minutes)")
        print("=" * 60 + "\n")
        
        start_time = time.time()
        check_interval = 2  # Check every 2 seconds
        
        while time.time() - start_time < timeout:
            try:
                # Check if CAPTCHA is still present
                if not self.detect_captcha(page):
                    print("\n" + "=" * 60)
                    print("✅ CAPTCHA solved! Resuming scraping...")
                    print("=" * 60 + "\n")
                    time.sleep(2)  # Brief pause to ensure page is ready
                    return True
                
                # Show progress indicator
                elapsed = int(time.time() - start_time)
                remaining = timeout - elapsed
                if elapsed % 10 == 0:  # Update every 10 seconds
                    print(f"⏳ Waiting for CAPTCHA solve... ({remaining}s remaining)")
                
                time.sleep(check_interval)
                
            except Exception as e:
                print(f"Warning: Error checking CAPTCHA status: {e}")
                time.sleep(check_interval)
        
        print("\n" + "=" * 60)
        print("❌ CAPTCHA solve timeout!")
        print("=" * 60)
        print("The CAPTCHA was not solved within the timeout period.")
        print("Please try again or use --use-session with a saved session.")
        print("=" * 60 + "\n")
        return False
    
    def random_delay(self, min_seconds: float = 1.5, max_seconds: float = 4.0):
        """
        Add a random delay to mimic human behavior.
        
        Args:
            min_seconds: Minimum delay in seconds
            max_seconds: Maximum delay in seconds
        """
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
    
    def human_like_scroll(self, page, direction: str = "down"):
        """
        Perform human-like scrolling with random patterns.
        
        Args:
            page: Playwright page object
            direction: "down" or "up"
        """
        try:
            # Random scroll distance
            if direction == "down":
                scroll_amount = random.randint(300, 800)
                page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            else:
                scroll_amount = random.randint(300, 800)
                page.evaluate(f"window.scrollBy(0, -{scroll_amount})")
            
            # Random delay after scroll
            self.random_delay(0.5, 1.5)
        except Exception as e:
            print(f"Warning: Error during human-like scroll: {e}")
    
    def move_mouse_randomly(self, page):
        """
        Move mouse to random position to mimic human behavior.
        
        Args:
            page: Playwright page object
        """
        try:
            # Get viewport size
            viewport = page.viewport_size
            if viewport:
                x = random.randint(100, viewport['width'] - 100)
                y = random.randint(100, viewport['height'] - 100)
                page.mouse.move(x, y)
        except Exception as e:
            print(f"Warning: Error moving mouse: {e}")
    
    def scroll_to_load_comments(self, page, max_scrolls: int = 20):
        """
        Scroll the page to load more comments with human-like behavior.
        
        Args:
            page: Playwright page object
            max_scrolls: Maximum number of scroll attempts
        """
        print("Loading comments (scrolling with human-like behavior)...")
        previous_comment_count = 0
        no_change_count = 0
        
        for i in range(max_scrolls):
            # Check for CAPTCHA before scrolling
            if self.detect_captcha(page):
                if not self.wait_for_captcha_solve(page):
                    print("Failed to solve CAPTCHA, stopping scroll.")
                    break
            
            # Human-like mouse movement
            self.move_mouse_randomly(page)
            
            # Human-like scrolling
            self.human_like_scroll(page, direction="down")
            
            # Random delay to mimic reading
            self.random_delay(2, 4)
            
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
        self.random_delay(1, 2)
    
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
        Main scraping method with CAPTCHA handling and session management.
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.validate_url():
            return False
        
        print(f"\nStarting TikTok Comment Scraper")
        print(f"URL: {self.url}")
        print(f"Output: {self.output_file}")
        print(f"Headless Mode: {self.headless}")
        print(f"Use Session: {self.use_session}")
        print("-" * 50)
        
        try:
            with sync_playwright() as p:
                print("Launching browser...")
                if not self.headless:
                    print("ℹ️  Browser window is visible for CAPTCHA solving")
                
                browser = p.chromium.launch(headless=self.headless)
                
                # Create context with realistic settings
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    viewport={'width': 1920, 'height': 1080},
                    locale='en-US',
                    timezone_id='America/New_York'
                )
                
                # Load session if requested
                if self.use_session:
                    print("Loading saved session...")
                    self.load_session(context)
                
                page = context.new_page()
                
                # Apply localStorage if available
                if self.use_session:
                    # Navigate first, then apply localStorage
                    print(f"Loading TikTok video...")
                    try:
                        page.goto(self.url, wait_until='domcontentloaded', timeout=30000)
                        self.apply_local_storage(page)
                        # Reload to apply localStorage
                        page.reload(wait_until='domcontentloaded', timeout=30000)
                    except Exception as e:
                        print(f"Warning: Error loading with session: {e}")
                else:
                    print(f"Loading TikTok video...")
                    try:
                        page.goto(self.url, wait_until='networkidle', timeout=30000)
                    except Exception as e:
                        print(f"Warning: Page load timeout, continuing anyway: {e}")
                        page.goto(self.url, timeout=30000)
                
                # Wait a bit for dynamic content with random delay
                self.random_delay(2, 4)
                
                # Check for CAPTCHA immediately after page load
                if self.detect_captcha(page):
                    print("\n⚠️  CAPTCHA detected on page load!")
                    if not self.wait_for_captcha_solve(page):
                        print("Failed to solve CAPTCHA. Exiting.")
                        browser.close()
                        return False
                    
                    # Save session after successful CAPTCHA solve
                    print("Saving session for future use...")
                    self.save_session(context)
                
                # Check if page loaded successfully
                try:
                    # Look for video or content indicators
                    page.wait_for_selector('video, [data-e2e="browse-video"]', timeout=10000)
                    print("✓ Video page loaded successfully")
                except Exception:
                    print("Warning: Could not verify video loaded. Attempting to continue...")
                
                # Scroll to load all comments
                self.scroll_to_load_comments(page)
                
                # Final CAPTCHA check before extraction
                if self.detect_captcha(page):
                    print("\n⚠️  CAPTCHA detected before comment extraction!")
                    if not self.wait_for_captcha_solve(page):
                        print("Failed to solve CAPTCHA. Exiting.")
                        browser.close()
                        return False
                    
                    # Save session after successful CAPTCHA solve
                    self.save_session(context)
                
                # Extract comments
                self.comments = self.extract_comments(page)
                
                # Save session if we successfully scraped without using a session
                if not self.use_session and self.comments:
                    print("\nSaving session for future use...")
                    self.save_session(context)
                    print("💡 Tip: Use --use-session flag next time to avoid CAPTCHA")
                
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
        description='TikTok Comment Scraper - Extract comments from TikTok videos with CAPTCHA handling',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --url "https://www.tiktok.com/@username/video/1234567890"
  %(prog)s --url "https://www.tiktok.com/@user/video/123" --output my_comments.csv
  %(prog)s --url "https://www.tiktok.com/@user/video/123" --use-session
  %(prog)s --url "https://www.tiktok.com/@user/video/123" --headless

CAPTCHA Handling:
  - Browser runs in VISIBLE mode by default (for manual CAPTCHA solving)
  - When CAPTCHA appears, solve it manually in the browser window
  - Session is saved automatically after solving CAPTCHA
  - Use --use-session on subsequent runs to avoid repeated CAPTCHAs

Important Notes:
  - This scraper only works with PUBLIC TikTok videos
  - No login/authentication is required or supported
  - Please respect TikTok's Terms of Service
  - Use responsibly and avoid overwhelming servers with requests
  - Built-in anti-detection features (random delays, human-like behavior)
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
        '--use-session',
        action='store_true',
        help='Use saved browser session to avoid CAPTCHA (load cookies from previous run)'
    )
    
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run browser in headless mode (not recommended - cannot solve CAPTCHA manually)'
    )
    
    args = parser.parse_args()
    
    # Warn if using headless mode
    if args.headless:
        print("\n⚠️  WARNING: Running in headless mode!")
        print("You will NOT be able to solve CAPTCHAs manually.")
        print("Consider running without --headless for better success rate.\n")
    
    # Create scraper instance
    scraper = TikTokScraper(
        url=args.url,
        output_file=args.output,
        headless=args.headless,
        use_session=args.use_session
    )
    
    # Run scraper
    success = scraper.scrape()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
