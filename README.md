# ClearRecon Trustee Sales Scraper

A Flask web application that automatically searches ClearRecon's California trustee sales listings and delivers results via email.

## Features

- 🏠 **Automated Trustee Sales Search** - Search by city and date range
- 📧 **Email Delivery** - Professional CSV reports sent via Gmail
- 🌐 **Web Interface** - User-friendly search form
- 📊 **CSV Export** - Download results directly
- 🤖 **Human-like Scraping** - Selenium-based automation

## Setup

1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and configure your Gmail credentials
4. Run: `python app.py`

## Environment Variables

Create a `.env` file with:

```
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-gmail@gmail.com
SENDER_PASSWORD=your-app-password
```

## Usage

1. Visit the web interface
2. Select a city and date range
3. Enter your email (optional)
4. Click "Search Trustee Sales"
5. Receive results via email or download CSV

## Deployment

This app is configured for deployment on Render, Railway, or similar platforms.

## Tech Stack

- **Backend**: Flask, Python
- **Scraping**: Selenium, BeautifulSoup
- **Email**: SMTP (Gmail)
- **Frontend**: HTML, CSS, JavaScript
