from flask import Flask, render_template, request, jsonify, send_file
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
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

app = Flask(__name__)

class ClearReconScraper:
    def __init__(self):
        self.driver = None
        self.counties = []
        
    def setup_driver(self):
        """Setup Chrome driver with human-like options"""
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Remove webdriver property to avoid detection
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return self.driver
    
    def human_type(self, element, text, delay=0.1):
        """Type text character by character to mimic human typing"""
        element.clear()
        for char in text:
            element.send_keys(char)
            time.sleep(delay)
    
    def get_counties(self):
        """Extract available counties from the website"""
        try:
            self.setup_driver()
            print("Navigating to ClearRecon...")
            
            # Navigate to the disclaimer page
            self.driver.get('https://clearrecon-ca.com/california-listings/')
            
            # Wait for page to load and accept terms
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Agree"))
            )
            
            # Click agree with human-like delay
            time.sleep(2)
            agree_button = self.driver.find_element(By.LINK_TEXT, "Agree")
            agree_button.click()
            
            # Wait for listings page to load
            time.sleep(3)
            
            # Look for county/city filters or dropdowns
            county_elements = []
            
            # Try to find county/location filters
            try:
                # Look for select elements that might contain counties
                selects = self.driver.find_elements(By.TAG_NAME, "select")
                for select in selects:
                    options = select.find_elements(By.TAG_NAME, "option")
                    for option in options:
                        text = option.text.strip()
                        if text and len(text) > 2:  # Filter out empty or very short options
                            county_elements.append(text)
                
                # Look for links or buttons that might represent counties
                links = self.driver.find_elements(By.TAG_NAME, "a")
                for link in links:
                    text = link.text.strip()
                    if any(keyword in text.lower() for keyword in ['county', 'sacramento', 'los angeles', 'san francisco', 'orange']):
                        county_elements.append(text)
                
            except Exception as e:
                print(f"Error finding county elements: {e}")
            
            # Default counties if we can't extract them
            if not county_elements:
                county_elements = [
                    'Sacramento County',
                    'Los Angeles County', 
                    'Orange County',
                    'San Francisco County',
                    'San Diego County',
                    'Alameda County',
                    'Santa Clara County',
                    'Riverside County',
                    'San Bernardino County',
                    'Contra Costa County'
                ]
            
            self.counties = sorted(list(set(county_elements)))
            print(f"Found {len(self.counties)} counties")
            
            return self.counties
            
        except Exception as e:
            print(f"Error getting counties: {e}")
            # Return default counties
            return [
                'Sacramento County',
                'Los Angeles County', 
                'Orange County',
                'San Francisco County',
                'San Diego County',
                'Alameda County',
                'Santa Clara County',
                'Riverside County',
                'San Bernardino County',
                'Contra Costa County'
            ]
        finally:
            if self.driver:
                self.driver.quit()
    
    def scrape_listings(self, city, start_date, end_date, progress_callback=None):
        """Scrape listings with improved navigation and multiple strategies"""
        try:
            # First try to setup driver for real scraping
            try:
                self.setup_driver()
                listings = []
            except Exception as driver_error:
                print(f"ChromeDriver error: {driver_error}")
                if progress_callback:
                    progress_callback("ChromeDriver unavailable, using mock data for demonstration...")
                # Use mock data as fallback
                from mock_data_generator import generate_mock_trustee_sales
                mock_listings = generate_mock_trustee_sales(city, 15)
                filtered_mock = self.filter_listings(mock_listings, city, start_date, end_date)
                if progress_callback:
                    progress_callback(f"Generated {len(mock_listings)} mock listings, {len(filtered_mock)} match criteria")
                return filtered_mock
            
            if progress_callback:
                progress_callback("Navigating to ClearRecon...")
            
            # Strategy 1: Try multiple entry points
            entry_urls = [
                'https://clearrecon-ca.com/california-listings/',
                'https://clearrecon-ca.com/listings/',
                'https://clearrecon-ca.com/foreclosure-listings/',
                'https://clearrecon-ca.com/trustee-sales/',
                'https://clearrecon-ca.com/'
            ]
            
            for url in entry_urls:
                try:
                    if progress_callback:
                        progress_callback(f"Trying {url}...")
                    
                    self.driver.get(url)
                    time.sleep(3)
                    
                    # Check if we need to accept terms
                    try:
                        agree_link = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.LINK_TEXT, "Agree"))
                        )
                        time.sleep(2)
                        agree_link.click()
                        time.sleep(3)
                        if progress_callback:
                            progress_callback("Terms accepted...")
                    except:
                        pass  # No terms to accept
                    
                    # Look for search forms
                    search_forms = self.driver.find_elements(By.TAG_NAME, "form")
                    
                    for form in search_forms:
                        try:
                            # Check if this form looks like a search form
                            form_text = form.text.lower()
                            if any(keyword in form_text for keyword in ['search', 'county', 'date', 'filter']):
                                if progress_callback:
                                    progress_callback("Found search form, filling it out...")
                                
                                # Fill out county field
                                county_inputs = form.find_elements(By.XPATH, ".//input[contains(@name, 'county') or contains(@placeholder, 'county')] | .//select[contains(@name, 'county')]")
                                for county_input in county_inputs:
                                    if county_input.tag_name == 'select':
                                        select = Select(county_input)
                                        options = [opt.text for opt in select.options]
                                        sacramento_option = next((opt for opt in options if 'sacramento' in opt.lower()), None)
                                        if sacramento_option:
                                            select.select_by_visible_text(sacramento_option)
                                    else:
                                        county_input.clear()
                                        self.human_type(county_input, county)
                                
                                # Fill out date fields
                                date_inputs = form.find_elements(By.XPATH, ".//input[contains(@type, 'date') or contains(@name, 'date')]")
                                for date_input in date_inputs:
                                    if 'start' in date_input.get_attribute('name').lower() or 'from' in date_input.get_attribute('name').lower():
                                        date_input.clear()
                                        self.human_type(date_input, start_date)
                                    elif 'end' in date_input.get_attribute('name').lower() or 'to' in date_input.get_attribute('name').lower():
                                        date_input.clear()
                                        self.human_type(date_input, end_date)
                                
                                # Submit the form
                                submit_button = form.find_element(By.XPATH, ".//input[@type='submit'] | .//button[@type='submit'] | .//button[contains(text(), 'Search')]")
                                time.sleep(1)
                                submit_button.click()
                                time.sleep(5)
                                
                                if progress_callback:
                                    progress_callback("Form submitted, extracting results...")
                                
                                # Extract listings from results
                                form_listings = self.extract_listings_from_page()
                                if form_listings:
                                    listings.extend(form_listings)
                                    if progress_callback:
                                        progress_callback(f"Found {len(form_listings)} listings from form")
                        
                        except Exception as e:
                            print(f"Error with form: {e}")
                            continue
                    
                    # Also try to extract listings directly from current page
                    direct_listings = self.extract_listings_from_page()
                    if direct_listings:
                        listings.extend(direct_listings)
                        if progress_callback:
                            progress_callback(f"Found {len(direct_listings)} listings directly")
                    
                    # If we found listings, break out of the URL loop
                    if listings:
                        break
                        
                except Exception as e:
                    print(f"Error with URL {url}: {e}")
                    continue
            
            # Strategy 2: Try JavaScript execution to load dynamic content
            if not listings:
                if progress_callback:
                    progress_callback("Trying JavaScript execution for dynamic content...")
                
                try:
                    # Execute JavaScript to trigger any dynamic loading
                    self.driver.execute_script("""
                        // Try to trigger any AJAX calls or dynamic loading
                        if (typeof jQuery !== 'undefined') {
                            jQuery(document).trigger('ready');
                        }
                        
                        // Scroll to trigger lazy loading
                        window.scrollTo(0, document.body.scrollHeight);
                        
                        // Click any "Load More" or "Show All" buttons
                        var loadButtons = document.querySelectorAll('button, a');
                        for (var i = 0; i < loadButtons.length; i++) {
                            var text = loadButtons[i].textContent.toLowerCase();
                            if (text.includes('load') || text.includes('show') || text.includes('more') || text.includes('all')) {
                                loadButtons[i].click();
                                break;
                            }
                        }
                    """)
                    
                    time.sleep(5)  # Wait for dynamic content to load
                    
                    js_listings = self.extract_listings_from_page()
                    if js_listings:
                        listings.extend(js_listings)
                        if progress_callback:
                            progress_callback(f"Found {len(js_listings)} listings via JavaScript")
                
                except Exception as e:
                    print(f"Error with JavaScript execution: {e}")
            
            # Strategy 3: Try searching for specific terms
            if not listings:
                if progress_callback:
                    progress_callback("Trying search functionality...")
                
                search_terms = [f"{county} trustee sale", f"{county} foreclosure", "sacramento auction"]
                
                for term in search_terms:
                    try:
                        # Look for search input
                        search_inputs = self.driver.find_elements(By.XPATH, "//input[@type='search'] | //input[@name='s'] | //input[@placeholder*='search']")
                        
                        for search_input in search_inputs:
                            search_input.clear()
                            self.human_type(search_input, term)
                            search_input.send_keys(Keys.RETURN)
                            time.sleep(3)
                            
                            search_listings = self.extract_listings_from_page()
                            if search_listings:
                                listings.extend(search_listings)
                                if progress_callback:
                                    progress_callback(f"Found {len(search_listings)} listings from search: {term}")
                                break
                        
                        if listings:
                            break
                            
                    except Exception as e:
                        print(f"Error with search term {term}: {e}")
                        continue
            
            if progress_callback:
                progress_callback(f"Scraping complete. Found {len(listings)} total listings.")
            
            # Filter by county and date range
            filtered_listings = self.filter_listings(listings, county, start_date, end_date)
            
            if progress_callback:
                progress_callback(f"After filtering: {len(filtered_listings)} listings match criteria.")
            
            return filtered_listings
            
        except Exception as e:
            print(f"Error in scrape_listings: {e}")
            if progress_callback:
                progress_callback(f"Error occurred: {str(e)}")
            return []
    
    def extract_listings_from_page(self):
        """Extract listings from current page using multiple strategies"""
        listings = []
        
        try:
            # Strategy 1: Look for tables
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            for table in tables:
                rows = table.find_elements(By.TAG_NAME, "tr")
                if len(rows) > 1:  # Has headers and data
                    try:
                        headers = [th.text.strip().lower() for th in rows[0].find_elements(By.XPATH, ".//th | .//td")]
                        
                        # Check if this looks like a property table
                        if any(keyword in ' '.join(headers) for keyword in ['address', 'date', 'amount', 'property', 'sale']):
                            for row in rows[1:]:
                                cols = row.find_elements(By.XPATH, ".//td | .//th")
                                if len(cols) >= 2:
                                    row_data = {'source': 'table'}
                                    for i, col in enumerate(cols):
                                        col_text = col.text.strip()
                                        if col_text and i < len(headers) and headers[i]:
                                            row_data[headers[i].replace(' ', '_')] = col_text
                                    
                                    if len([v for v in row_data.values() if v and len(str(v)) > 3]) >= 2:
                                        listings.append(row_data)
                    except Exception as e:
                        print(f"Error processing table: {e}")
            
            # Strategy 2: Look for structured divs/containers
            containers = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'property') or contains(@class, 'listing') or contains(@class, 'item') or contains(@class, 'result')]")
            
            for container in containers:
                try:
                    text_content = container.text.strip()
                    if len(text_content) > 50:  # Substantial content
                        listing_data = {
                            'source': 'container',
                            'raw_text': text_content
                        }
                        
                        # Try to extract structured data
                        if re.search(r'\d+\s+[A-Za-z\s]+(?:St|Street|Ave|Avenue|Rd|Road|Dr|Drive|Blvd|Boulevard|Way|Ct|Court)', text_content):
                            listing_data['has_address'] = True
                        
                        if re.search(r'\$[\d,]+(?:\.\d{2})?', text_content):
                            listing_data['has_amount'] = True
                        
                        if re.search(r'\d{1,2}/\d{1,2}/\d{4}', text_content):
                            listing_data['has_date'] = True
                        
                        # Only add if it has at least 2 property indicators
                        indicators = sum([listing_data.get('has_address', False), 
                                        listing_data.get('has_amount', False), 
                                        listing_data.get('has_date', False)])
                        
                        if indicators >= 2 or 'sacramento' in text_content.lower():
                            listings.append(listing_data)
                
                except Exception as e:
                    print(f"Error processing container: {e}")
            
            # Strategy 3: Look for any elements with property-related text
            all_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Sacramento') or contains(text(), 'trustee') or contains(text(), 'foreclosure') or contains(text(), 'auction')]")
            
            for element in all_elements:
                try:
                    text = element.text.strip()
                    if len(text) > 30 and len(text) < 500:  # Reasonable length
                        # Check if it contains property-like information
                        if (re.search(r'\d+\s+[A-Za-z\s]+(?:St|Street|Ave|Avenue|Rd|Road)', text) or 
                            re.search(r'\$[\d,]+', text) or 
                            'sacramento' in text.lower()):
                            
                            listings.append({
                                'source': 'text_element',
                                'content': text,
                                'tag': element.tag_name
                            })
                
                except Exception as e:
                    print(f"Error processing text element: {e}")
        
        except Exception as e:
            print(f"Error in extract_listings_from_page: {e}")
        
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
        # Return common California cities where trustee sales occur
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
