# PhishingLens - Chrome Extension

Advanced 4-source AI phishing detection with real-time blocking and whitelist management.

## Features

✅ **4-Source AI Analysis**: Integrates with your backend's 4-source fusion system
✅ **Real-time Blocking**: Automatically blocks phishing sites with warning pages
✅ **Whitelist Management**: Add trusted sites to bypass detection
✅ **Visual Notifications**: Browser notifications for phishing alerts
✅ **Source Analysis**: Shows which AI sources detected the threat
✅ **Modern UI**: Clean, responsive interface with status indicators

## Installation

1. **Load in Chrome**:
   - Open Chrome and go to `chrome://extensions/`
   - Enable "Developer mode" (top right toggle)
   - Click "Load unpacked" and select this extension folder

2. **Configure Backend**:
   - Update `config.js` with your backend URL (default: `http://localhost:8000`)
   - Ensure your 4-source API is running on `/analyze_url_v2` endpoint

## Usage

### Automatic Protection
- Extension automatically scans every page you visit
- Badge shows status: ✓ (safe), 🚨 (phishing), ? (error)
- Phishing sites are blocked with warning page

### Manual Analysis
- Click extension icon to see detailed analysis
- View 4-source breakdown and confidence scores
- Manage whitelist from popup

### Whitelist Management
- Add sites to whitelist from warning page or popup
- Remove sites from whitelist in popup
- Supports wildcard patterns (e.g., `*.example.com`)

## API Integration

The extension connects to your backend's `/analyze_url_v2` endpoint:

```javascript
POST /analyze_url_v2
{
  "url": "https://example.com"
}

Response:
{
  "final_verdict": true,
  "confidence": 0.85,
  "sources": {
    "scanner": {"fired": true, "score": 0.8},
    "hf": {"fired": false, "score": 0.3},
    "graph": {"fired": true, "score": 0.9},
    "otx": {"fired": false, "score": 0.1}
  }
}
```

## Testing

See `test-phishing-sites.md` for known phishing sites to test with.

## Permissions

- `activeTab`: Access current tab URL
- `storage`: Store whitelist data
- `notifications`: Show phishing alerts
- `tabs`: Navigate and block tabs
- `<all_urls>`: Analyze all websites

## Files

- `manifest.json`: Extension configuration
- `background.js`: Service worker for URL analysis
- `popup.html/js`: Extension popup interface
- `config.js`: Backend API configuration
- `test-phishing-sites.md`: Test sites for validation
