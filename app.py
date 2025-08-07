from flask import Flask, render_template, request, jsonify, send_file
import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
import time
import csv
from datetime import datetime, timedelta
import threading
import tempfile
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Ensure downloads directory exists for CSV exports
DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), 'downloads')
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

app = Flask(__name__)

@app.route('/test_playwright')
def test_playwright():
    import asyncio
    import sys
    from playwright.async_api import async_playwright

    async def run():
        print('Launching Playwright browser...', file=sys.stdout, flush=True)
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                print('Browser launched.', file=sys.stdout, flush=True)
                page = await browser.new_page()
                await page.goto('https://example.com', timeout=60000)
                print('Navigated to example.com', file=sys.stdout, flush=True)
                title = await page.title()
                await browser.close()
                print(f'Page title: {title}', file=sys.stdout, flush=True)
                return title
        except Exception as e:
            print(f'Playwright error: {e}', file=sys.stdout, flush=True)
            return f'Error: {e}'

    title = asyncio.run(run())
    return f"Page title: {title}"

class ClearReconScraper:
    def __init__(self):
        pass
        
    # Playwright does not require manual driver setup. All browser/page setup will be handled in each method.
    
    # Playwright's .fill() and .type() handle input natively; no need for a separate human_type method.
    
    async def get_cities_async(self):
        """Extract available cities from the website using Playwright async API"""
        try:
            from playwright.async_api import async_playwright
            city_elements = []
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto('https://clearrecon-ca.com/california-listings/', timeout=60000)

                # Accept terms if present
                try:
                    agree = await page.query_selector("text=Agree")
                    if agree:
                        await agree.click()
                        await page.wait_for_timeout(2000)
                except Exception:
                    pass
                await page.wait_for_timeout(3000)

                # Look for select elements that might contain counties
                selects = await page.query_selector_all('select')
                for select in selects:
                    options = await select.query_selector_all('option')
                    for option in options:
                        text = (await option.inner_text()).strip()
                        if text and len(text) > 2 and 'city' in text.lower():
                            city_elements.append(text)

                # Look for links or buttons that might represent counties
                links = await page.query_selector_all('a')
                for link in links:
                    text = (await link.inner_text()).strip()
                    # Try to pick out city names from links, e.g. 'Sacramento', 'Los Angeles', etc.
                    if any(city in text for city in ['Sacramento', 'Los Angeles', 'San Francisco', 'San Diego', 'Oakland', 'Fresno', 'Long Beach', 'Santa Ana', 'Anaheim', 'Riverside', 'Stockton', 'Bakersfield', 'Fremont', 'San Jose', 'Modesto', 'Fontana', 'Oxnard', 'Moreno Valley', 'Huntington Beach', 'Glendale', 'Santa Clarita', 'Garden Grove', 'Oceanside', 'Rancho Cucamonga', 'Ontario', 'Corona', 'Elk Grove', 'Palmdale', 'Salinas', 'Pomona', 'Hayward', 'Escondido', 'Torrance', 'Sunnyvale', 'Orange', 'Fullerton', 'Pasadena', 'Thousand Oaks', 'Visalia', 'Simi Valley', 'Concord', 'Roseville', 'Victorville', 'Santa Rosa', 'Vallejo', 'Berkeley', 'El Monte', 'Downey', 'Costa Mesa', 'Inglewood']):
                        city_elements.append(text)
                await browser.close()

            if not city_elements:
                city_elements = [
                    'Sacramento', 'Los Angeles', 'San Francisco', 'San Diego', 'Oakland',
                    'Fresno', 'Long Beach', 'Santa Ana', 'Anaheim', 'Riverside',
                    'Stockton', 'Bakersfield', 'Fremont', 'San Jose', 'Modesto',
                    'Fontana', 'Oxnard', 'Moreno Valley', 'Huntington Beach', 'Glendale',
                    'Santa Clarita', 'Garden Grove', 'Oceanside', 'Rancho Cucamonga',
                    'Ontario', 'Corona', 'Elk Grove', 'Palmdale', 'Salinas', 'Pomona',
                    'Hayward', 'Escondido', 'Torrance', 'Sunnyvale', 'Orange',
                    'Fullerton', 'Pasadena', 'Thousand Oaks', 'Visalia', 'Simi Valley',
                    'Concord', 'Roseville', 'Victorville', 'Santa Rosa', 'Vallejo',
                    'Berkeley', 'El Monte', 'Downey', 'Costa Mesa', 'Inglewood'
                ]
            print(f"Found {len(set(city_elements))} cities")
            return sorted(list(set(city_elements)))
        except Exception as e:
            print(f"Error getting cities: {e}")
            return [
                'Sacramento', 'Los Angeles', 'San Francisco', 'San Diego', 'Oakland',
                'Fresno', 'Long Beach', 'Santa Ana', 'Anaheim', 'Riverside',
                'Stockton', 'Bakersfield', 'Fremont', 'San Jose', 'Modesto',
                'Fontana', 'Oxnard', 'Moreno Valley', 'Huntington Beach', 'Glendale',
                'Santa Clarita', 'Garden Grove', 'Oceanside', 'Rancho Cucamonga',
                'Ontario', 'Corona', 'Elk Grove', 'Palmdale', 'Salinas', 'Pomona',
                'Hayward', 'Escondido', 'Torrance', 'Sunnyvale', 'Orange',
                'Fullerton', 'Pasadena', 'Thousand Oaks', 'Visalia', 'Simi Valley',
                'Concord', 'Roseville', 'Victorville', 'Santa Rosa', 'Vallejo',
                'Berkeley', 'El Monte', 'Downey', 'Costa Mesa', 'Inglewood'
            ]

    
    async def scrape_listings_async(self, city, start_date, end_date, progress_callback=None):
        """Scrape listings with improved navigation and multiple strategies using Playwright async API"""
        try:
            from playwright.async_api import async_playwright
            entry_urls = [
                'https://clearrecon-ca.com/california-listings/',
                'https://clearrecon-ca.com/listings/',
                'https://clearrecon-ca.com/foreclosure-listings/',
                'https://clearrecon-ca.com/trustee-sales/',
                'https://clearrecon-ca.com/'
            ]
            listings = []
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                for url in entry_urls:
                    try:
                        if progress_callback:
                            progress_callback(f"Trying {url}...")
                        await page.goto(url, timeout=60000)
                        await page.wait_for_timeout(3000)
                        # Accept terms if present
                        try:
                            agree = await page.query_selector("text=Agree")
                            if agree:
                                await agree.click()
                                await page.wait_for_timeout(2000)
                                if progress_callback:
                                    progress_callback("Terms accepted...")
                        except Exception:
                            pass
                        # Try to find a form and fill it out
                        forms = await page.query_selector_all('form')
                        for form in forms:
                            form_text = (await form.inner_text()).lower()
                            if any(keyword in form_text for keyword in ['search', 'county', 'date', 'filter']):
                                if progress_callback:
                                    progress_callback("Found search form, filling it out...")
                                # Fill county/city
                                county_inputs = await form.query_selector_all("input[name*='county'], input[placeholder*='county'], select[name*='county']")
                                for county_input in county_inputs:
                                    tag = await county_input.get_property('tagName')
                                    tag = (await tag.json_value()).lower()
                                    if tag == 'select':
                                        options = await county_input.query_selector_all('option')
                                        for option in options:
                                            option_text = (await option.inner_text()).lower()
                                            if 'sacramento' in option_text:
                                                await county_input.select_option(label=option_text)
                                    else:
                                        await county_input.fill(city)
                                # Fill dates
                                date_inputs = await form.query_selector_all("input[type='date'], input[name*='date']")
                                for date_input in date_inputs:
                                    name = (await date_input.get_attribute('name') or '').lower()
                                    if 'start' in name or 'from' in name:
                                        await date_input.fill(start_date)
                                    elif 'end' in name or 'to' in name:
                                        await date_input.fill(end_date)
                                # Submit form
                                submit_btn = await form.query_selector("input[type='submit'], button[type='submit'], button:has-text('Search')")
                                if submit_btn:
                                    await submit_btn.click()
                                    await page.wait_for_timeout(3000)
                        # Extract listings from the page
                        html = await page.content()
                        soup = BeautifulSoup(html, 'html.parser')
                        # Use the same logic as extract_listings_from_page_async
                        listings = self.extract_listings_from_html(soup)
                        if listings:
                            break
                    except Exception as e:
                        print(f"Error scraping {url}: {e}")
                await browser.close()
            return listings
        except Exception as e:
            print(f"Error scraping listings: {e}")
            return []

    def extract_listings_from_html(self, soup):
        """Extract listings from a BeautifulSoup HTML soup object using table/container/text strategies."""
        listings = []
        try:
            # Strategy 1: Look for tables
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                if len(rows) > 1:
                    try:
                        headers = [th.get_text(strip=True).lower() for th in rows[0].find_all(['th', 'td'])]
                        if any(keyword in ' '.join(headers) for keyword in ['address', 'date', 'amount', 'property', 'sale']):
                            for row in rows[1:]:
                                cols = row.find_all(['td', 'th'])
                                if len(cols) >= 2:
                                    row_data = {'source': 'table'}
                                    for i, col in enumerate(cols):
                                        col_text = col.get_text(strip=True)
                                        if col_text and i < len(headers) and headers[i]:
                                            row_data[headers[i].replace(' ', '_')] = col_text
                                    if len([v for v in row_data.values() if v and len(str(v)) > 3]) >= 2:
                                        listings.append(row_data)
                    except Exception as e:
                        print(f"Error processing table: {e}")
            # Strategy 2: Look for structured divs/containers
            containers = soup.select("div.property, div.listing, div.item, div.result")
            for container in containers:
                try:
                    text_content = container.get_text(strip=True)
                    if len(text_content) > 50:
                        listing_data = {
                            'source': 'container',
                            'raw_text': text_content
                        }
                        if re.search(r'\d+\s+[A-Za-z\s]+(?:St|Street|Ave|Avenue|Rd|Road|Dr|Drive|Blvd|Boulevard|Way|Ct|Court)', text_content):
                            listing_data['has_address'] = True
                        if re.search(r'\$[\d,]+(?:\.\d{2})?', text_content):
                            listing_data['has_amount'] = True
                        if re.search(r'\d{1,2}/\d{1,2}/\d{4}', text_content):
                            listing_data['has_date'] = True
                        indicators = sum([listing_data.get('has_address', False), listing_data.get('has_amount', False), listing_data.get('has_date', False)])
                        if indicators >= 2 or 'sacramento' in text_content.lower():
                            listings.append(listing_data)
                except Exception as e:
                    print(f"Error processing container: {e}")
            # Strategy 3: Look for any elements with property-related text
            keywords = ['Sacramento', 'trustee', 'foreclosure', 'auction']
            for element in soup.find_all(text=lambda t: any(k.lower() in t.lower() for k in keywords)):
                try:
                    text = element.strip()
                    if 30 < len(text) < 500:
                        if (re.search(r'\d+\s+[A-Za-z\s]+(?:St|Street|Ave|Avenue|Rd|Road)', text) or re.search(r'\$[\d,]+', text) or 'sacramento' in text.lower()):
                            listings.append({'source': 'text_element', 'content': text})
                except Exception as e:
                    print(f"Error processing text element: {e}")
        except Exception as e:
            print(f"Error in extract_listings_from_html: {e}")
        return listings

    
    def filter_listings(self, listings, city, start_date, end_date):
        """Filter listings by city (extracted from address) and date range"""
        filtered = []
        
        for listing in listings:
            # Extract city from address or raw text
            city_match = False
            text_content = listing.get('raw_text', '').lower()
            address = listing.get('address', '').lower()
            
            # Check if the specified city appears in the address or text content
            if city.lower() in address or city.lower() in text_content:
                city_match = True
                # Add extracted city to the listing
                listing['extracted_city'] = city
            else:
                # Try to extract city from address using common patterns
                import re
                # Look for city patterns in address (city, state format)
                city_pattern = r'([A-Za-z\s]+),\s*CA'
                match = re.search(city_pattern, address + ' ' + text_content)
                if match:
                    extracted_city = match.group(1).strip().title()
                    listing['extracted_city'] = extracted_city
                    # Check if extracted city matches the requested city
                    if city.lower() in extracted_city.lower():
                        city_match = True
                else:
                    # Fallback: look for city name anywhere in the text
                    if city.lower() in (address + ' ' + text_content).lower():
                        city_match = True
                        listing['extracted_city'] = city
            
            # Date filtering can be enhanced based on actual date format found
            # For now, include all listings that match city
            if city_match:
                filtered.append(listing)
        
        return filtered

# Global scraper instance
scraper = ClearReconScraper()

@app.route('/')
def index():
    """Main page with search form"""
    return render_template('index.html')

@app.route('/get_cities')
def get_cities():
    """API endpoint to get available cities"""
    try:
        # Optionally, call Playwright async city extraction here if needed
        cities = [
            'Sacramento', 'Los Angeles', 'San Francisco', 'San Diego', 'Oakland',
            'Fresno', 'Long Beach', 'Santa Ana', 'Anaheim', 'Riverside',
            'Stockton', 'Bakersfield', 'Fremont', 'San Jose', 'Modesto',
            'Fontana', 'Oxnard', 'Moreno Valley', 'Huntington Beach', 'Glendale',
            'Santa Clarita', 'Garden Grove', 'Oceanside', 'Rancho Cucamonga',
            'Ontario', 'Corona', 'Elk Grove', 'Palmdale', 'Salinas', 'Pomona',
            'Hayward', 'Escondido', 'Torrance', 'Sunnyvale', 'Orange',
            'Fullerton', 'Pasadena', 'Thousand Oaks', 'Visalia', 'Simi Valley',
            'Concord', 'Roseville', 'Victorville', 'Santa Rosa', 'Vallejo',
            'Berkeley', 'El Monte', 'Downey', 'Costa Mesa', 'Inglewood'
        ]
        return jsonify(sorted(cities))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/search', methods=['POST'])
def search():
    """Handle search request"""
    try:
        data = request.json
        email = data.get('email', '')
        city = data.get('city', 'Sacramento')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        # Start scraping in background thread
        def scrape_and_download():
            try:
                # Progress tracking (in real app, you'd use websockets or similar)
                def progress_callback(message):
                    print(f"Progress: {message}")
                
                listings = scraper.scrape_listings(city, start_date, end_date, progress_callback)
                
                if listings:
                    # Save to CSV
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    csv_filename = f'clearrecon_listings_{city.replace(" ", "_")}_{timestamp}.csv'
                    
                    # Create CSV
                    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                        if listings:
                            fieldnames = list(listings[0].keys())
                            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                            writer.writeheader()
                            writer.writerows(listings)
                    
                    # Send email if provided
                    if email:
                        send_email(email, csv_filename, city, start_date, end_date, len(listings))
                
            except Exception as e:
                print(f"Error in background scraping: {e}")
        
        # Start background thread
        thread = threading.Thread(target=scrape_and_download)
        thread.start()
        
        return jsonify({'status': 'started', 'message': 'Scraping started. Check back for download link when complete.'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/search_sync', methods=['POST'])
def search_sync():
    """Synchronous search for immediate results"""
    try:
        data = request.json
        email = data.get('email', '')
        city = data.get('city', 'Sacramento')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        listings = scraper.scrape_listings(city, start_date, end_date)
        
        # Save to CSV
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_filename = f'clearrecon_listings_{city.replace(" ", "_")}_{timestamp}.csv'
        
        if listings:
            with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = list(listings[0].keys())
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(listings)
            
            # Send email if provided
            if email:
                send_email(email, csv_filename, city, start_date, end_date, len(listings))
        
        return jsonify({
            'status': 'complete',
            'listings': listings,
            'count': len(listings),
            'csv_file': csv_filename
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def send_email(to_email, csv_file, city, start_date, end_date, count):
    """Send email with CSV attachment using environment variables for credentials"""
    try:
        # Use environment variables or default values for email configuration
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        sender_email = os.getenv('SENDER_EMAIL', 'clearrecon.scraper@gmail.com')  # Service account
        sender_password = os.getenv('SENDER_PASSWORD', '')  # App password from env
        
        if not sender_password:
            print("Warning: No email password configured. Set SENDER_PASSWORD environment variable.")
            return False
        
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = f'ClearRecon Trustee Sales Report - {city}'
        
        body = f'''Please find attached the trustee sales report.

Search Parameters:
- City: {city}
- Date Range: {start_date} to {end_date}
- Total Listings Found: {count}

This report was generated automatically by the ClearRecon Trustee Sales Scraper.

Best regards,
ClearRecon Scraper Bot'''
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach CSV file
        with open(csv_file, 'rb') as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
        
        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename= {os.path.basename(csv_file)}'
        )
        msg.attach(part)
        
        # Send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, to_email, text)
        server.quit()
        
        print(f"Email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

@app.route('/download/<filename>')
def download_file(filename):
    """Serve CSV file for download"""
    try:
        downloads_dir = os.path.join(os.path.dirname(__file__), 'downloads')
        file_path = os.path.join(downloads_dir, filename)
        
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True, download_name=filename)
        else:
            return jsonify({'error': 'File not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/downloads')
def list_downloads():
    """List available download files"""
    try:
        downloads_dir = os.path.join(os.path.dirname(__file__), 'downloads')
        if not os.path.exists(downloads_dir):
            return jsonify({'files': []})
            
        files = []
        for filename in os.listdir(downloads_dir):
            if filename.endswith('.csv'):
                file_path = os.path.join(downloads_dir, filename)
                file_info = {
                    'filename': filename,
                    'size': os.path.getsize(file_path),
                    'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S'),
                    'download_url': f'/download/{filename}'
                }
                files.append(file_info)
                
        # Sort by modification time (newest first)
        files.sort(key=lambda x: x['modified'], reverse=True)
        return jsonify({'files': files})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
