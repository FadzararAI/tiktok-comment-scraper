# TikTok Comment Scraper

A Python-based tool for extracting comments, replies, and user information from public TikTok videos. This scraper uses browser automation to handle dynamic content and includes **manual CAPTCHA solving functionality** to ensure reliable scraping. All data is saved to CSV format.

## ⚠️ Important Disclaimer

**This tool is for educational and research purposes only.** Please note:

- Only works with **PUBLIC** TikTok videos (no authentication)
- Respect TikTok's [Terms of Service](https://www.tiktok.com/legal/terms-of-service)
- Respect TikTok's [robots.txt](https://www.tiktok.com/robots.txt)
- Use responsibly - do not overload servers with excessive requests
- Rate limiting and human-like behavior built-in
- The scraper may break if TikTok changes their website structure
- For commercial use, consider TikTok's official API

## Features

✨ **Core Functionality:**
- Extract all comments from public TikTok videos
- Capture replies (nested comments)
- Pagination support to fetch ALL comments
- Export data to clean CSV format

🔐 **CAPTCHA Handling (NEW!):**
- **Automatic CAPTCHA detection** - detects when TikTok shows verification challenges
- **Manual CAPTCHA solving** - runs browser in visible mode for you to solve CAPTCHAs
- **Session persistence** - saves cookies after successful CAPTCHA solve
- **Session reuse** - use `--use-session` to avoid repeated CAPTCHAs
- **Automatic resume** - continues scraping after CAPTCHA is solved

🤖 **Anti-Detection Features:**
- Human-like scrolling patterns with random speeds
- Random delays between actions (2-5 seconds)
- Mouse movement simulation
- Realistic browser profile (user-agent, viewport, locale)
- Rate limiting to respect TikTok's servers

📊 **Data Captured:**
- Username
- Comment text
- Number of likes
- Timestamp
- Reply indicators
- Comment IDs

🛡️ **Robust Design:**
- Error handling for invalid URLs, network issues, and rate limiting
- Progress indicators during scraping
- CAPTCHA timeout handling (5 minutes)
- Clear console messages and status updates

## Requirements

- Python 3.8 or higher
- Chrome/Chromium browser (installed automatically by Playwright)

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/FadzararAI/tiktok-comment-scraper.git
   cd tiktok-comment-scraper
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Playwright browsers:**
   ```bash
   playwright install chromium
   ```
   
   This will download the Chromium browser needed for automation.

## Usage

### Basic Usage

Extract comments from a TikTok video (browser window will be visible):

```bash
python tiktok_scraper.py --url "https://www.tiktok.com/@username/video/1234567890"
```

This will:
- Open a **visible browser window** (for CAPTCHA solving if needed)
- Scrape all comments with human-like behavior
- Save results to `comments.csv`
- Save session for future use

### Using Saved Session (Avoid CAPTCHAs)

After first successful run, use saved session to avoid CAPTCHAs:

```bash
python tiktok_scraper.py --url "https://www.tiktok.com/@username/video/1234567890" --use-session
```

This reuses cookies from a previous successful scrape, significantly reducing CAPTCHA frequency.

### Custom Output File

Specify a custom output filename:

```bash
python tiktok_scraper.py --url "https://www.tiktok.com/@username/video/1234567890" --output my_comments.csv
```

### Headless Mode (Not Recommended)

Run in headless mode (WARNING: cannot solve CAPTCHAs manually):

```bash
python tiktok_scraper.py --url "https://www.tiktok.com/@username/video/1234567890" --headless
```

⚠️ **Not recommended** - you won't be able to solve CAPTCHAs if they appear.

### Command-Line Options

```
usage: tiktok_scraper.py [-h] --url URL [--output OUTPUT] [--use-session] [--headless]

Options:
  -h, --help         Show help message and exit
  --url URL          TikTok video URL (required)
  --output OUTPUT    Output CSV filename (default: comments.csv)
  --use-session      Use saved browser session to avoid CAPTCHA
  --headless         Run in headless mode (not recommended)
```

## 🔐 CAPTCHA Handling

### How It Works

TikTok may show CAPTCHA challenges to verify you're human. This scraper handles CAPTCHAs through **manual solving**:

1. **Automatic Detection**: The scraper continuously monitors for CAPTCHA challenges
2. **Browser Visibility**: Browser runs in **visible mode by default** (not headless)
3. **User Prompt**: When CAPTCHA detected, you'll see:
   ```
   ⚠️  CAPTCHA DETECTED!
   Please solve the CAPTCHA in the browser window.
   The scraper will automatically continue once solved.
   ```
4. **Manual Solve**: Switch to the browser window and solve the CAPTCHA (puzzle, slider, etc.)
5. **Auto-Resume**: Once solved, scraping automatically continues
6. **Session Save**: Your session is saved to avoid future CAPTCHAs

### Session Management

**First Run:**
```bash
python tiktok_scraper.py --url "https://www.tiktok.com/@user/video/123"
# May require CAPTCHA solve
# Session saved to sessions/tiktok_session.json
```

**Subsequent Runs:**
```bash
python tiktok_scraper.py --url "https://www.tiktok.com/@user/video/456" --use-session
# Loads saved session, likely NO CAPTCHA needed!
```

**Session Storage:**
- Sessions are saved in `sessions/tiktok_session.json`
- Contains cookies and localStorage data
- Reusable across different videos
- Automatically saved after successful CAPTCHA solve

### CAPTCHA Timeout

- Default timeout: **5 minutes** (300 seconds)
- If you don't solve within timeout, scraping stops
- You can retry by running the command again
- Progress indicator shows remaining time

### Tips for Avoiding CAPTCHAs

1. ✅ **Use `--use-session`** after first successful run
2. ✅ **Wait between scrapes** - don't scrape too frequently
3. ✅ **Scrape during off-peak hours** when TikTok has lower traffic
4. ✅ **Use human-like behavior** (built-in: random delays, scrolling)
5. ✅ **Don't run multiple instances** simultaneously
6. ❌ **Don't use --headless** - you won't be able to solve CAPTCHAs
7. ❌ **Don't scrape too many videos** in quick succession

## Output Format

The scraper generates a CSV file with the following columns:

| Column | Description | Example |
|--------|-------------|---------|
| `comment_id` | Unique identifier for the comment | `comment_1` |
| `username` | Commenter's username | `@johndoe` |
| `comment_text` | Content of the comment | `"This is amazing!"` |
| `likes` | Number of likes on the comment | `152` |
| `timestamp` | When comment was posted | `2024-01-15` or `2h ago` |
| `is_reply` | Whether this is a reply to another comment | `True` or `False` |
| `reply_to` | Username or ID being replied to | `@janedoe` |

### Example Output

```csv
comment_id,username,comment_text,likes,timestamp,is_reply,reply_to
comment_1,@user123,"Love this video!",45,2024-01-15,False,
comment_2,@user456,"Thanks for sharing",12,2024-01-15,False,
comment_3,@user789,"Agreed!",8,2024-01-16,True,@user123
```

## How It Works

1. **URL Validation:** Checks if the provided URL is a valid TikTok video URL
2. **Browser Launch:** Opens Chromium browser using Playwright (visible by default)
3. **Session Loading:** If `--use-session` is used, loads saved cookies
4. **Page Load:** Navigates to the TikTok video URL
5. **CAPTCHA Check:** Continuously monitors for CAPTCHA challenges
6. **Manual Solve:** If CAPTCHA appears, waits for you to solve it manually
7. **Scrolling:** Automatically scrolls with human-like behavior to load all comments
8. **Extraction:** Parses the DOM to extract comment data
9. **Session Save:** Saves cookies/session for future use
10. **CSV Export:** Saves all data to a structured CSV file

## Error Handling

The scraper includes robust error handling for:

- ❌ Invalid URLs - Validates TikTok URL format before scraping
- ❌ Network errors - Handles timeouts and connection issues
- ❌ **CAPTCHA detection** - Automatically detects and prompts for manual solving
- ❌ **CAPTCHA timeout** - Handles cases where CAPTCHA isn't solved in time
- ❌ Rate limiting - Built-in delays to avoid overwhelming servers
- ❌ Missing elements - Gracefully handles missing data fields
- ❌ Changed page structure - Provides clear error messages
- ❌ Session loading errors - Falls back to normal scraping if session invalid

## Limitations

- **Public videos only** - Cannot access private or age-restricted content
- **No authentication** - Does not support logging in to TikTok
- **CAPTCHA challenges** - TikTok may show CAPTCHAs (manual solving supported)
- **Rate limits** - TikTok may rate-limit excessive requests
- **Page structure changes** - May break if TikTok updates their website
- **Regional restrictions** - Some videos may not be available in all regions
- **Large comment counts** - Very popular videos with 10,000+ comments may take longer
- **Session expiry** - Saved sessions expire after some time (days/weeks)

## Troubleshooting

### CAPTCHA Issues

**"CAPTCHA DETECTED" message appears:**
- ✅ This is normal! Switch to the browser window and solve it manually
- ✅ Follow the on-screen instructions (slide puzzle, click images, etc.)
- ✅ The scraper will automatically continue after you solve it
- ✅ Your session will be saved to avoid future CAPTCHAs

**"CAPTCHA solve timeout":**
- You took too long to solve (> 5 minutes)
- Run the command again and solve faster
- Or use `--use-session` if you've solved before

**Frequent CAPTCHAs:**
- Use `--use-session` to reuse your saved session
- Wait longer between scrapes (hours, not minutes)
- Don't run multiple scrapers simultaneously
- Check that `sessions/tiktok_session.json` exists

### General Issues

**"No comments found":**
- Verify the video is public and has comments
- The video might be region-restricted
- Try using `--use-session` if you have a saved session
- CAPTCHA might be blocking access

**"Invalid TikTok URL":**
- Ensure URL format: `https://www.tiktok.com/@username/video/1234567890`
- Check for typos in the URL

**Browser installation issues:**
- Run `playwright install chromium` again
- On Linux, you may need: `playwright install-deps chromium`

**Timeout errors:**
- Your internet connection may be slow
- TikTok might be rate-limiting your requests
- CAPTCHA might be present (browser should be visible to check)
- Try again after a few minutes

**Session not loading:**
- Check that `sessions/tiktok_session.json` exists
- Session might be expired - delete it and create a new one
- Try running without `--use-session` first

## Development

### Project Structure

```
tiktok-comment-scraper/
├── tiktok_scraper.py      # Main scraper script with CAPTCHA handling
├── requirements.txt       # Python dependencies
├── README.md             # Documentation (this file)
├── example_output.csv    # Example CSV output
└── sessions/             # Session storage (created automatically)
    └── tiktok_session.json  # Saved browser session (cookies, localStorage)
```

**Note:** The `sessions/` directory is created automatically when you first solve a CAPTCHA.

### Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Legal & Ethics

**Please use this tool responsibly:**

- ✅ Respect TikTok's Terms of Service
- ✅ Only scrape public content
- ✅ Use reasonable rate limits
- ✅ Include proper attribution if publishing scraped data
- ✅ Consider privacy implications
- ❌ Don't use for spam or harassment
- ❌ Don't overload TikTok's servers
- ❌ Don't violate any applicable laws

For commercial projects, use TikTok's official API when available.

## License

This project is provided as-is for educational purposes. Use at your own risk.

## Support

If you encounter issues:
1. Check the [Troubleshooting](#troubleshooting) section
2. Verify your Python and dependency versions
3. Open an issue on GitHub with:
   - Error message
   - Python version
   - Operating system
   - Steps to reproduce

---

**Made with ❤️ for educational purposes**
