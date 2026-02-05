# TikTok Comment Scraper

A Python-based tool for extracting comments, replies, and user information from public TikTok videos. This scraper uses browser automation to handle dynamic content and saves all data to CSV format.

## ⚠️ Important Disclaimer

**This tool is for educational and research purposes only.** Please note:

- Only works with **PUBLIC** TikTok videos (no authentication)
- Respect TikTok's [Terms of Service](https://www.tiktok.com/legal/terms-of-service)
- Respect TikTok's [robots.txt](https://www.tiktok.com/robots.txt)
- Use responsibly - do not overload servers with excessive requests
- Rate limiting is built-in to mimic human behavior
- The scraper may break if TikTok changes their website structure
- For commercial use, consider TikTok's official API

## Features

✨ **Core Functionality:**
- Extract all comments from public TikTok videos
- Capture replies (nested comments)
- Pagination support to fetch ALL comments
- Export data to clean CSV format

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
- User-agent headers for better compatibility
- Scrolling/pagination to load all comments

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

Extract comments from a TikTok video:

```bash
python tiktok_scraper.py --url "https://www.tiktok.com/@username/video/1234567890"
```

This will create a `comments.csv` file with all extracted comments.

### Custom Output File

Specify a custom output filename:

```bash
python tiktok_scraper.py --url "https://www.tiktok.com/@username/video/1234567890" --output my_comments.csv
```

### Debug Mode (Show Browser)

Run with visible browser window for debugging:

```bash
python tiktok_scraper.py --url "https://www.tiktok.com/@username/video/1234567890" --no-headless
```

### Command-Line Options

```
usage: tiktok_scraper.py [-h] --url URL [--output OUTPUT] [--no-headless]

Options:
  -h, --help         Show help message and exit
  --url URL          TikTok video URL (required)
  --output OUTPUT    Output CSV filename (default: comments.csv)
  --no-headless      Show browser window during scraping
```

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
2. **Browser Launch:** Opens a headless Chromium browser using Playwright
3. **Page Load:** Navigates to the TikTok video URL
4. **Scrolling:** Automatically scrolls to load all comments (pagination)
5. **Extraction:** Parses the DOM to extract comment data
6. **CSV Export:** Saves all data to a structured CSV file

## Error Handling

The scraper includes robust error handling for:

- ❌ Invalid URLs - Validates TikTok URL format before scraping
- ❌ Network errors - Handles timeouts and connection issues
- ❌ Rate limiting - Built-in delays to avoid overwhelming servers
- ❌ Missing elements - Gracefully handles missing data fields
- ❌ Changed page structure - Provides clear error messages

## Limitations

- **Public videos only** - Cannot access private or age-restricted content
- **No authentication** - Does not support logging in to TikTok
- **Rate limits** - TikTok may rate-limit excessive requests
- **Page structure changes** - May break if TikTok updates their website
- **Regional restrictions** - Some videos may not be available in all regions
- **Large comment counts** - Very popular videos with 10,000+ comments may take longer

## Troubleshooting

### "No comments found"
- Verify the video is public and has comments
- Try using `--no-headless` to see what's happening
- The video might be region-restricted

### "Invalid TikTok URL"
- Ensure URL format: `https://www.tiktok.com/@username/video/1234567890`
- Check for typos in the URL

### Browser installation issues
- Run `playwright install chromium` again
- On Linux, you may need: `playwright install-deps chromium`

### Timeout errors
- Your internet connection may be slow
- TikTok might be rate-limiting your requests
- Try again after a few minutes

## Development

### Project Structure

```
tiktok-comment-scraper/
├── tiktok_scraper.py   # Main scraper script
├── requirements.txt    # Python dependencies
└── README.md          # Documentation (this file)
```

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
