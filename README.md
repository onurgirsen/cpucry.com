# Polymarket Dashboard - Standalone Website

A real-time Polymarket prediction market analytics dashboard with Black-Scholes pricing model.

## Features

- 📊 Real-time market data from Polymarket
- 📈 Black-Scholes fair value calculations
- 🏆 Top opportunities ranking by ROI
- ✨ Visual change highlighting (green for new, yellow for changed)
- 📱 Responsive design

## Files

```
website/
├── index.html      # Main HTML structure
├── styles.css      # All CSS styles
├── config.js       # Configuration (API endpoints, companies)
├── blackscholes.js # Black-Scholes model implementation
├── api.js          # API fetching logic
├── app.js          # Main application logic
└── README.md       # This file
```

## Deployment

### Option 1: Static Hosting (Recommended)

Upload all files to any static hosting service:
- **GitHub Pages**: Free, just push to a repo
- **Netlify**: Free tier, drag and drop
- **Vercel**: Free tier, connects to Git
- **Cloudflare Pages**: Free, fast CDN

### Option 2: Local Testing

1. Open a terminal in the `website` folder
2. Start a local server:
   ```bash
   # Python 3
   python -m http.server 8000
   
   # Node.js (if you have npx)
   npx serve .
   ```
3. Open `http://localhost:8000` in your browser

### Option 3: Direct File Opening

**Note**: Some browsers block API calls from `file://` URLs. Use a local server instead.

## Configuration

Edit `config.js` to customize:

- **AUTO_REFRESH_MS**: How often to refresh data (default: 30 seconds)
- **RESOLUTION_DATE**: Market expiration date
- **RISK_FREE_RATE**: Interest rate for Black-Scholes
- **COMPANIES**: Add or remove tracked companies

### CORS Proxy

If you encounter CORS errors, you can use a CORS proxy:

```javascript
// In config.js
CORS_PROXY: 'https://corsproxy.io/?'
```

## API Sources

- **Polymarket Gamma API**: Event and market data
- **Polymarket CLOB API**: Order book data
- **Yahoo Finance**: Stock prices and historical volatility

## Browser Support

- Chrome 80+
- Firefox 75+
- Safari 13+
- Edge 80+

## License

MIT License - Feel free to use and modify!
