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
            
            # Calculate session age if timestamp available
            if 'timestamp' in session_data:
                try:
                    session_age = datetime.now() - datetime.fromisoformat(session_data['timestamp'])
                    print(f"✓ Session age: {session_age.days} days")
                except Exception:
                    print("✓ Session loaded (age unknown)")
            else:
                print("✓ Session loaded (age unknown)")
            
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
                    page.evaluate("({key, value}) => window.localStorage.setItem(key, value)", 
                                  {'key': key, 'value': value})
                print(f"✓ Applied {len(self.session_local_storage)} localStorage items")
            except Exception as e:
                print(f"Warning: Could not apply localStorage: {e}")
    

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
    
    def click_comments_button(self, page) -> bool:
        """
        Click the Comments tab button to load the comments section.
        Tries multiple selectors as fallback in case TikTok changes class names.
        
        Args:
            page: Playwright page object
            
        Returns:
            bool: True if button was clicked successfully, False otherwise
        """
        print("Clicking Comments tab...")
        
        # Multiple selectors to try (in order of preference)
        selectors = [
            'button#comments',
            'button[id="comments"]',
            'button.TUXTabBar-itemTitle:has-text("Comments")',
            'button:has-text("Comments")'
        ]
        
        for selector in selectors:
            try:
                # Try to find and click the button with this selector
                button = page.wait_for_selector(selector, timeout=5000, state='visible')
                button.click()
                print("✓ Comments tab clicked")
                return True
            except PlaywrightTimeoutError:
                continue
            except Exception as e:
                print(f"Note: Selector '{selector}' failed: {e}")
                continue
        
        print("⚠️ Could not find Comments button, trying to proceed anyway...")
        return False
    
    def wait_for_comments_section(self, page) -> bool:
        """
        Wait for the comments section to load after clicking the Comments button.
        IMPORTANT: The container exists immediately but content changes from videos to comments.
        
        Args:
            page: Playwright page object
            
        Returns:
            bool: True if comments section loaded, False otherwise
        """
        print("Waiting for comments to load...")
        
        # Step 1: Wait for the tab content container to be visible
        try:
            page.wait_for_selector('.TUXTabBar-content', state='visible', timeout=10000)
            print("✓ Comments container found")
        except PlaywrightTimeoutError:
            print("❌ Could not find comments container (.TUXTabBar-content)")
            return False
        except Exception as e:
            print(f"❌ Error waiting for comments container: {e}")
            return False
        
        # Step 2: CRITICAL - Wait for content transformation
        # The container exists immediately but content takes time to change from videos to comments
        # This is necessary because TikTok dynamically swaps content in the same container
        print("Waiting for content transformation (videos → comments)...")
        time.sleep(3)  # Required: Give time for content to swap (based on TikTok's behavior)
        
        # Step 3: Wait for actual comment elements to appear
        print("Waiting for comment items to appear...")
        comment_selectors = [
            '.TUXTabBar-content [data-e2e="comment-item"]',
            '.TUXTabBar-content div[class*="CommentItem"]',
            '.TUXTabBar-content div[class*="comment-item"]',
            '.TUXTabBar-content div[class*="comment"]'
        ]
        
        for selector in comment_selectors:
            try:
                page.wait_for_selector(selector, timeout=10000, state='visible')
                # Count how many we found
                count = page.locator(selector).count()
                print(f"✓ Found {count} comments using selector: {selector}")
                return True
            except PlaywrightTimeoutError:
                print(f"Note: Selector '{selector}' timed out")
                continue
            except Exception as e:
                print(f"Note: Selector '{selector}' failed: {e}")
                continue
        
        print("⚠️ Could not find comment elements in container")
        print("⚠️ The container may be empty or selectors may need updating")
        return False
    
    def scroll_to_load_comments(self, page, max_scrolls: int = 20, max_retries: int = 3):
        """
        Scroll within the comments container to load more comments.
        Uses correct selector for top-level comments.
        
        Args:
            page: Playwright page object
            max_scrolls: Maximum number of scroll attempts
            max_retries: Maximum number of retries when no new comments load
        """
        print("Scrolling to load all comments...")
        last_count = 0
        no_change_count = 0
        
        # Correct selector for top-level comments
        comment_selector = '.css-1mzopna-7937d88b--DivCommentObjectWrapper'
        
        for i in range(max_scrolls):
            # Count current top-level comments
            try:
                current_comments = page.locator(comment_selector).count()
            except Exception as e:
                print(f"Warning: Error counting comments: {e}")
                current_comments = last_count
            
            # Scroll WITHIN the comments container using scrollBy for incremental scrolling
            try:
                page.evaluate('''
                    () => {
                        const container = document.querySelector('.TUXTabBar-content');
                        if (container) {
                            container.scrollBy(0, 1000);
                        }
                    }
                ''')
            except Exception as e:
                print(f"Warning: Error scrolling container: {e}")
            
            # Wait for new comments to load
            self.random_delay(2, 3)
            
            # Check if new comments loaded
            if current_comments > last_count:
                print(f"  Loaded {current_comments} comments...")
                last_count = current_comments
                no_change_count = 0  # Reset retry counter
            else:
                no_change_count += 1
                print(f"  No new comments (attempt {no_change_count}/{max_retries})")
                
                if no_change_count >= max_retries:
                    print(f"✓ Finished scrolling. Total top-level comments: {last_count}")
                    break
        
        return last_count
    
    def handle_replies(self, page, parent_comment_elem, comments_data, parent_username, parent_index):
        """
        Click 'View replies' button and extract nested comments.
        
        Args:
            page: Playwright page object
            parent_comment_elem: Parent comment element
            comments_data: List to append reply comments to
            parent_username: Username of parent commenter
            parent_index: Index of parent comment
        """
        try:
            # Look for "View replies" button with multiple selectors
            reply_button_selectors = [
                'button.TUXButton:has-text("View")',
                'button:has-text("replies")',
                'button.TUXButton--borderless:has-text("View")',
                'button:has-text("View")'
            ]
            
            reply_button = None
            for selector in reply_button_selectors:
                try:
                    reply_button = parent_comment_elem.query_selector(selector)
                    if reply_button:
                        break
                except Exception:
                    continue
            
            if reply_button:
                # Get reply count from button text
                try:
                    button_text = reply_button.inner_text(timeout=1000)
                    print(f"    → Clicking: {button_text}")
                    
                    # Click to expand replies
                    reply_button.click()
                    time.sleep(1.5)  # Wait for replies to load
                    
                    # Now extract the reply comments using correct class selector
                    # Replies use: css-7waxo-7937d88b--DivCommentItemWrapper
                    reply_elements = parent_comment_elem.query_selector_all('.css-7waxo-7937d88b--DivCommentItemWrapper')
                    
                    print(f"    ✓ Found {len(reply_elements)} replies")
                    
                    for j, reply_elem in enumerate(reply_elements):
                        try:
                            # Extract reply username
                            reply_username = "Unknown"
                            username_selectors = [
                                'p.TUXText--weight-medium[style*="font-size: 14px"]',
                                'p.css-u0d6t3-7937d88b--StyledTUXText',
                                'p.TUXText.TUXText--weight-medium'
                            ]
                            for selector in username_selectors:
                                try:
                                    username_elem = reply_elem.query_selector(selector)
                                    if username_elem:
                                        reply_username = username_elem.inner_text(timeout=1000)
                                        break
                                except Exception:
                                    continue
                            
                            # Extract reply text
                            reply_text = ""
                            text_selectors = [
                                'span[data-e2e="comment-text"]',
                                'p[data-e2e="comment-text"]',
                                'span.TUXText:not([style*="color: var(--ui-text-3)"])'
                            ]
                            for selector in text_selectors:
                                try:
                                    text_elem = reply_elem.query_selector(selector)
                                    if text_elem:
                                        reply_text = text_elem.inner_text(timeout=1000)
                                        break
                                except Exception:
                                    continue
                            
                            # Extract reply likes
                            reply_likes = "0"
                            likes_selectors = [
                                'span.TUXText--weight-normal[style*="color: var(--ui-text-3)"]',
                                'span.TUXText[style*="color: var(--ui-text-3)"][style*="font-size: 14px"]'
                            ]
                            for selector in likes_selectors:
                                try:
                                    likes_elem = reply_elem.query_selector(selector)
                                    if likes_elem:
                                        likes_text = likes_elem.inner_text(timeout=1000)
                                        # Check if it's actually a number (not "Reply" or other text)
                                        if likes_text.strip().replace('K', '').replace('M', '').replace('.', '').replace(',', '').isdigit():
                                            reply_likes = likes_text
                                            break
                                except Exception:
                                    continue
                            
                            reply_data = {
                                'username': reply_username.strip(),
                                'comment_text': reply_text.strip(),
                                'likes': reply_likes.strip(),
                                'is_reply': True,
                                'reply_to': parent_username,
                                'comment_id': f'comment_{parent_index}_reply_{j}'
                            }
                            
                            comments_data.append(reply_data)
                            print(f"      ↳ {reply_username}: {reply_text[:40] if reply_text else ''}... (Likes: {reply_likes})")
                            
                        except Exception as e:
                            print(f"⚠️ Error extracting reply {j}: {e}")
                            continue
                except Exception as e:
                    print(f"⚠️ Error clicking reply button: {e}")
                    
        except Exception as e:
            print(f"⚠️ Error handling replies: {e}")
    
    def extract_comments(self, page) -> List[Dict]:
        """
        Extract comments using correct CSS selectors for TikTok's structure.
        
        Args:
            page: Playwright page object
            
        Returns:
            List of comment dictionaries
        """
        comments_data = []
        print("\nExtracting comments...")
        
        try:
            # Wait for comments container
            try:
                page.wait_for_selector('.TUXTabBar-content', timeout=10000)
                print("✓ Comments container found")
            except Exception as e:
                print(f"❌ Could not find comments container: {e}")
                return []
            
            # Get all TOP-LEVEL comment wrappers using correct selector
            top_level_comments = page.query_selector_all('.css-1mzopna-7937d88b--DivCommentObjectWrapper')
            
            print(f"✓ Found {len(top_level_comments)} top-level comments")
            
            for i, comment_elem in enumerate(top_level_comments):
                try:
                    # Extract username - more flexible selector
                    username = None
                    username_selectors = [
                        'p.TUXText--weight-medium[style*="font-size: 14px"]',
                        'p.css-u0d6t3-7937d88b--StyledTUXText',
                        'p.TUXText.TUXText--weight-medium'
                    ]
                    for selector in username_selectors:
                        try:
                            username_elem = comment_elem.query_selector(selector)
                            if username_elem:
                                username = username_elem.inner_text(timeout=1000)
                                break
                        except Exception:
                            continue
                    
                    if not username:
                        username = "Unknown"
                    
                    # Extract comment text
                    comment_text = ""
                    text_selectors = [
                        'span[data-e2e="comment-text"]',
                        'p[data-e2e="comment-text"]',
                        'span.TUXText:not([style*="color: var(--ui-text-3)"])',  # Avoid like count
                    ]
                    for selector in text_selectors:
                        try:
                            text_elem = comment_elem.query_selector(selector)
                            if text_elem:
                                comment_text = text_elem.inner_text(timeout=1000)
                                break
                        except Exception:
                            continue
                    
                    # Extract likes - specific selector for gray text with numbers
                    likes = "0"
                    likes_selectors = [
                        'span.TUXText--weight-normal[style*="color: var(--ui-text-3)"]',
                        'span.TUXText[style*="color: var(--ui-text-3)"][style*="font-size: 14px"]',
                    ]
                    for selector in likes_selectors:
                        try:
                            likes_elem = comment_elem.query_selector(selector)
                            if likes_elem:
                                likes_text = likes_elem.inner_text(timeout=1000)
                                # Check if it's actually a number (not "Reply" or other text)
                                if likes_text.strip().replace('K', '').replace('M', '').replace('.', '').replace(',', '').isdigit():
                                    likes = likes_text
                                    break
                        except Exception:
                            continue
                    
                    # Extract timestamp (keeping existing logic)
                    timestamp = ""
                    try:
                        time_elem = comment_elem.query_selector('time, [datetime]')
                        if time_elem:
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
                    
                    comment_data = {
                        'username': username.strip(),
                        'comment_text': comment_text.strip(),
                        'likes': likes.strip(),
                        'timestamp': timestamp.strip(),
                        'is_reply': False,
                        'reply_to': '',
                        'comment_id': f'comment_{i}'
                    }
                    
                    comments_data.append(comment_data)
                    print(f"  [{i+1}] {username}: {comment_text[:50] if comment_text else ''}... (Likes: {likes})")
                    
                    # Check for "View replies" button and click it
                    self.handle_replies(page, comment_elem, comments_data, username, i)
                    
                except Exception as e:
                    print(f"⚠️ Error extracting comment {i}: {e}")
                    continue
            
            print(f"\n✓ Extracted {len([c for c in comments_data if not c['is_reply']])} top-level comments and {len([c for c in comments_data if c['is_reply']])} replies")
            
        except Exception as e:
            print(f"Error extracting comments: {e}")
        
        return comments_data
    
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
            # Ensure all columns exist
            for col in columns_order:
                if col not in df.columns:
                    df[col] = ''
            df = df[columns_order]
            
            df.to_csv(self.output_file, index=False, encoding='utf-8', quoting=csv.QUOTE_ALL)
            
            # Calculate stats
            top_level_count = len([c for c in comments if not c.get('is_reply', False)])
            reply_count = len([c for c in comments if c.get('is_reply', False)])
            
            print(f"\n✅ Scraping complete! Saved to {self.output_file}")
            print(f"   Total comments: {len(comments)} ({top_level_count} top-level, {reply_count} replies)")
        except Exception as e:
            print(f"Error saving to CSV: {e}")
            # Fallback to basic CSV writing
            try:
                with open(self.output_file, 'w', newline='', encoding='utf-8') as f:
                    fieldnames = ['comment_id', 'username', 'comment_text', 'likes', 'timestamp', 'is_reply', 'reply_to']
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
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
                    print(f"Navigating to video...")
                    try:
                        page.goto(self.url, wait_until='networkidle', timeout=30000)
                    except Exception as e:
                        print(f"Warning: Page load timeout, continuing anyway: {e}")
                        page.goto(self.url, timeout=30000)
                
                # Wait a bit for dynamic content with random delay
                self.random_delay(2, 4)
                
                # Check if page loaded successfully
                try:
                    # Look for video or content indicators
                    page.wait_for_selector('video, [data-e2e="browse-video"]', timeout=10000)
                    print("✓ Video page loaded successfully")
                except Exception:
                    print("Warning: Could not verify video loaded. Attempting to continue...")
                
                # CLICK THE COMMENTS BUTTON (CRITICAL STEP)
                # Note: Gracefully degrades if button not found, as UI structure may vary
                try:
                    self.click_comments_button(page)
                except Exception as e:
                    print(f"⚠️ Error clicking Comments button: {e}")
                    print("⚠️ Note: Comment extraction may fail if Comments tab wasn't clicked")
                
                # WAIT A MOMENT FOR PAGE TO REACT
                # TikTok shows CAPTCHA after clicking Comments, not on page load
                print("Waiting for page to respond to Comments click...")
                self.random_delay(2, 3)
                
                # ALWAYS PROMPT FOR CAPTCHA (NO DETECTION NEEDED)
                # Since CAPTCHA always appears after clicking Comments, just assume it's there
                print("\n" + "="*50)
                print("⚠️  CAPTCHA PROMPT")
                print("="*50)
                print("\nTikTok typically shows a CAPTCHA verification.")
                print("Please solve the CAPTCHA in the browser window.")
                print("Once you have completed it, press ENTER to continue...")
                
                try:
                    input()  # Wait for user to press ENTER
                    print("\n✅ Continuing scraping...")
                    
                    # Save session after user confirms CAPTCHA solved
                    print("Saving session for future use...")
                    self.save_session(context)
                    
                    # Brief pause to ensure page is ready
                    time.sleep(2)
                except KeyboardInterrupt:
                    print("\n\nScraping interrupted by user.")
                    browser.close()
                    return False
                
                # WAIT FOR COMMENTS SECTION TO LOAD
                # Note: Attempts to proceed even if section not detected, for resilience
                try:
                    self.wait_for_comments_section(page)
                except Exception as e:
                    print(f"⚠️ Error waiting for comments section: {e}")
                    print("⚠️ Note: Comment extraction may fail if section didn't load")
                
                # Scroll to load all comments
                self.scroll_to_load_comments(page)
                
                # Extract comments
                print("Extracting comments...")
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
  - After solving, press ENTER in the terminal to continue
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
