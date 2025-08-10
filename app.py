import os
import sqlite3
import requests
from flask import Flask, render_template, request, jsonify, send_file
from bs4 import BeautifulSoup
import logging
from werkzeug.utils import secure_filename
import tempfile
import json
import time
import random
import re
from urllib.parse import urljoin, urlparse, parse_qs
import traceback
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import base64

# Try to import optional dependencies
try:
    from fake_useragent import UserAgent
    FAKE_USERAGENT_AVAILABLE = True
except ImportError:
    FAKE_USERAGENT_AVAILABLE = False
    print("Warning: fake_useragent not installed. Using static user agent.")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Using environment variables only.")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24).hex())

# Database setup
DATABASE = 'court_data.db'

def init_db():
    """Initialize the database with required tables"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_type TEXT NOT NULL,
            case_number TEXT NOT NULL,
            filing_year TEXT NOT NULL,
            query_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            raw_response TEXT,
            status TEXT,
            parsed_data TEXT,
            is_blocked BOOLEAN DEFAULT 0,
            retry_count INTEGER DEFAULT 0,
            proxy_used TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS case_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_number TEXT NOT NULL,
            parties TEXT,
            filing_date TEXT,
            next_hearing_date TEXT,
            case_status TEXT,
            orders_count INTEGER DEFAULT 0,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

class DelhiHighCourtRealScraper:
    def __init__(self):
        self.base_url = "https://delhihighcourt.nic.in"
        self.case_status_url = f"{self.base_url}/case-status"
        self.search_url = f"{self.base_url}/app/get-case-type-status"
        
        # Setup Chrome options for headless browsing
        self.chrome_options = Options()
        self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.chrome_options.add_experimental_option('useAutomationExtension', False)
        
        if FAKE_USERAGENT_AVAILABLE:
            ua = UserAgent()
            self.chrome_options.add_argument(f"--user-agent={ua.random}")
        
        self.driver = None
        self.max_retries = 3
        self.retry_delay = 10
        
    def _setup_driver(self):
        """Initialize Chrome WebDriver"""
        try:
            self.driver = webdriver.Chrome(options=self.chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            return True
        except Exception as e:
            logger.error(f"Failed to setup Chrome driver: {e}")
            return False
    
    def _close_driver(self):
        """Close Chrome WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
    
    def get_case_types(self):
        """Return available case types"""
        return {
            'WP(C)': 'Writ Petition (Civil)',
            'CRL.A.': 'Criminal Appeal',
            'FAO': 'First Appeal from Order',
            'CM': 'Civil Misc',
            'CRL.M.C.': 'Criminal Misc Case',
            'CRL.REV.P.': 'Criminal Revision Petition',
            'MAT.APP.': 'Mat Appeal',
            'RFA': 'Regular First Appeal',
            'CRL.M.A.': 'Criminal Misc Application',
            'W.P.(CRL.)': 'Writ Petition (Criminal)'
        }

    def search_case_real(self, case_type, case_number, filing_year, retry_count=0):
        """
        Attempt real scraping from Delhi High Court website
        WARNING: This will likely be blocked by CAPTCHA
        """
        try:
            if not self._setup_driver():
                return self._fallback_to_mock(case_type, case_number, filing_year)
            
            logger.info(f"Attempting real scraping for: {case_type} {case_number}/{filing_year}")
            
            # Navigate to case status page
            self.driver.get(self.case_status_url)
            time.sleep(random.uniform(2, 5))
            
            # Check for CAPTCHA
            if self._captcha_detected():
                logger.warning("CAPTCHA detected - cannot proceed with automated scraping")
                self._close_driver()
                return {
                    'success': False,
                    'error': 'CAPTCHA detected. The Delhi High Court website requires manual verification. Please:\n'
                            '1. Visit https://delhihighcourt.nic.in/case-status manually\n'
                            '2. Use a CAPTCHA solving service\n'
                            '3. Try again later\n'
                            '4. Consider using official APIs if available',
                    'raw_html': self.driver.page_source,
                    'blocked': True,
                    'requires_captcha': True
                }
            
            # Try to fill the form
            result = self._fill_search_form(case_type, case_number, filing_year)
            self._close_driver()
            return result
            
        except Exception as e:
            logger.error(f"Real scraping failed: {str(e)}")
            self._close_driver()
            return self._fallback_to_mock(case_type, case_number, filing_year)
    
    def _captcha_detected(self):
        """Check if CAPTCHA is present on the page"""
        try:
            # Common CAPTCHA indicators
            captcha_selectors = [
                "img[src*='captcha']",
                "img[alt*='captcha']",
                "#captcha",
                ".captcha",
                "input[name*='captcha']",
                "canvas",  # Some sites use canvas-based CAPTCHAs
            ]
            
            for selector in captcha_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    logger.info(f"CAPTCHA detected with selector: {selector}")
                    return True
            
            # Check page source for CAPTCHA-related text
            page_source = self.driver.page_source.lower()
            captcha_keywords = ['captcha', 'verification', 'robot', 'human']
            
            for keyword in captcha_keywords:
                if keyword in page_source:
                    logger.info(f"CAPTCHA keyword detected: {keyword}")
                    return True
                    
            return False
            
        except Exception as e:
            logger.warning(f"Error checking for CAPTCHA: {e}")
            return True  # Assume CAPTCHA is present if we can't check
    
    def _fill_search_form(self, case_type, case_number, filing_year):
        """Attempt to fill and submit the search form"""
        try:
            wait = WebDriverWait(self.driver, 10)
            
            # Find and select case type
            case_type_select = wait.until(EC.presence_of_element_located((By.NAME, "case_type")))
            Select(case_type_select).select_by_value(case_type)
            
            # Fill case number
            case_number_input = self.driver.find_element(By.NAME, "case_no")
            case_number_input.clear()
            case_number_input.send_keys(case_number)
            
            # Fill year
            year_input = self.driver.find_element(By.NAME, "year")
            year_input.clear()
            year_input.send_keys(filing_year)
            
            # Submit form
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "input[type='submit'], button[type='submit']")
            submit_button.click()
            
            # Wait for results
            time.sleep(5)
            
            # Check for results
            page_source = self.driver.page_source
            
            if "No Record Found" in page_source or "no record found" in page_source.lower():
                return {
                    'success': False,
                    'error': 'No case found with the provided details',
                    'raw_html': page_source
                }
            
            # Parse the results
            return self._parse_real_response(page_source, case_type, case_number, filing_year)
            
        except TimeoutException:
            return {
                'success': False,
                'error': 'Timeout waiting for page elements. The website might be slow or structure changed.',
                'raw_html': self.driver.page_source if self.driver else None
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Error filling search form: {str(e)}',
                'raw_html': self.driver.page_source if self.driver else None
            }
    
    def _parse_real_response(self, html, case_type, case_number, filing_year):
        """Parse the actual response from Delhi High Court"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            case_data = {
                'case_number': f"{case_type} {case_number}/{filing_year}",
                'parties': {'petitioner': 'N/A', 'respondent': 'N/A'},
                'filing_date': 'N/A',
                'next_hearing_date': 'N/A',
                'case_status': 'N/A',
                'orders': [],
                'case_history': []
            }
            
            # Parse case details - these selectors need to be updated based on actual HTML
            # This is a template - you'll need to inspect the actual page structure
            
            # Extract parties
            parties_section = soup.find('div', class_='parties') or soup.find('table', id='case-details')
            if parties_section:
                petitioner = parties_section.find('td', string=re.compile('petitioner', re.I))
                if petitioner and petitioner.find_next_sibling():
                    case_data['parties']['petitioner'] = petitioner.find_next_sibling().get_text(strip=True)
                
                respondent = parties_section.find('td', string=re.compile('respondent', re.I))
                if respondent and respondent.find_next_sibling():
                    case_data['parties']['respondent'] = respondent.find_next_sibling().get_text(strip=True)
            
            # Extract dates
            date_cells = soup.find_all('td')
            for cell in date_cells:
                text = cell.get_text(strip=True)
                # Look for date patterns
                if re.search(r'\d{2}/\d{2}/\d{4}', text):
                    if 'filing' in cell.get_text().lower() or 'filed' in cell.get_text().lower():
                        case_data['filing_date'] = text
                    elif 'hearing' in cell.get_text().lower() or 'next' in cell.get_text().lower():
                        case_data['next_hearing_date'] = text
            
            # Extract case status
            status_cell = soup.find('td', string=re.compile('status', re.I))
            if status_cell and status_cell.find_next_sibling():
                case_data['case_status'] = status_cell.find_next_sibling().get_text(strip=True)
            
            # Extract orders
            orders_table = soup.find('table', {'class': 'orders'}) or soup.find('table', id='orders')
            if orders_table:
                rows = orders_table.find_all('tr')[1:]  # Skip header
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 3:
                        order = {
                            'date': cols[0].get_text(strip=True),
                            'order_type': cols[1].get_text(strip=True),
                            'description': cols[2].get_text(strip=True),
                            'pdf_link': self._extract_pdf_link(cols[2])
                        }
                        case_data['orders'].append(order)
            
            return {
                'success': True,
                'data': case_data,
                'raw_html': html,
                'source': 'real_scraping'
            }
            
        except Exception as e:
            logger.error(f"Error parsing real response: {e}")
            return self._fallback_to_mock(case_type, case_number, filing_year)
    
    def _extract_pdf_link(self, element):
        """Extract PDF download link from element"""
        try:
            link = element.find('a', href=True)
            if link and ('pdf' in link['href'].lower() or 'download' in link['href'].lower()):
                return urljoin(self.base_url, link['href'])
        except:
            pass
        return None
    
    def _fallback_to_mock(self, case_type, case_number, filing_year):
        """Fallback to mock data when real scraping fails"""
        logger.info("Falling back to mock data")
        return {
            'success': True,
            'data': self._generate_mock_response(case_type, case_number, filing_year),
            'raw_html': '<html><body>Mock response - real scraping failed</body></html>',
            'source': 'mock_data',
            'note': 'Real scraping failed, showing sample data structure'
        }
    
    def _generate_mock_response(self, case_type, case_number, filing_year):
        """Generate realistic mock response"""
        return {
            'case_number': f"{case_type} {case_number}/{filing_year}",
            'parties': {
                'petitioner': f"Sample Petitioner {case_number}",
                'respondent': "State of Delhi & Others"
            },
            'filing_date': f"15/03/{filing_year}",
            'next_hearing_date': "25/12/2024",
            'case_status': "Listed for hearing",
            'orders': [
                {
                    'date': '20/11/2024',
                    'order_type': 'Order',
                    'description': f'Case {case_type} {case_number}/{filing_year} adjourned to next date for final hearing',
                    'pdf_link': f'/orders/{case_type}_{case_number}_{filing_year}_order.pdf'
                },
                {
                    'date': '15/10/2024',
                    'order_type': 'Notice',
                    'description': 'Notice issued to all respondents to file reply',
                    'pdf_link': f'/orders/{case_type}_{case_number}_{filing_year}_notice.pdf'
                }
            ],
            'case_history': [
                {
                    'date': f'15/03/{filing_year}',
                    'event': 'Case filed and registered'
                },
                {
                    'date': '20/03/2024',
                    'event': 'First hearing scheduled'
                }
            ]
        }

    def search_case(self, case_type, case_number, filing_year):
        """Main search method - tries real scraping first, falls back to mock"""
        # Enable this line to attempt real scraping (will likely fail due to CAPTCHA)
        # return self.search_case_real(case_type, case_number, filing_year)
        
        # For now, return mock data with explanation
        mock_result = self._fallback_to_mock(case_type, case_number, filing_year)
        mock_result['explanation'] = {
            'why_mock': 'The Delhi High Court website uses CAPTCHA verification',
            'real_url': f'{self.search_url}',
            'manual_steps': [
                '1. Visit https://delhihighcourt.nic.in/case-status',
                '2. Select case type and enter case number/year',
                '3. Solve CAPTCHA verification',
                '4. Submit form to get real data'
            ],
            'automation_options': [
                'Use Selenium with manual CAPTCHA solving',
                'Integrate with CAPTCHA solving services (2captcha, Anti-Captcha)',
                'Use official APIs if available',
                'Implement manual intervention points'
            ]
        }
        return mock_result

# Update the Flask routes to use the new scraper
@app.route('/')
def index():
    """Render the main page"""
    try:
        scraper = DelhiHighCourtRealScraper()
        case_types = scraper.get_case_types()
        return render_template('index.html', case_types=case_types)
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        return f"Error loading page: {str(e)}", 500

@app.route('/search', methods=['POST'])
def search_case():
    """Handle case search requests"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Invalid JSON data'}), 400
            
        case_type = data.get('case_type', '').strip()
        case_number = data.get('case_number', '').strip()
        filing_year = data.get('filing_year', '').strip()
        
        logger.info(f"Received search request: {case_type} {case_number}/{filing_year}")
        
        # Validate inputs
        if not all([case_type, case_number, filing_year]):
            return jsonify({
                'success': False,
                'error': 'All fields are required'
            }), 400
        
        if not re.match(r'^\d{4}$', filing_year):
            return jsonify({
                'success': False,
                'error': 'Filing year must be a 4-digit year'
            }), 400
        
        # Initialize scraper and search
        scraper = DelhiHighCourtRealScraper()
        result = scraper.search_case(case_type, case_number, filing_year)
        
        # Log the query
        log_query(
            case_type, 
            case_number, 
            filing_year, 
            result.get('raw_html', ''),
            'success' if result['success'] else 'error',
            result.get('data', {}),
            result.get('blocked', False)
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in search_case: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': 'Internal server error. Please try again.'
        }), 500

# Add the rest of the Flask routes from the previous version...
@app.route('/download/<path:filename>')
def download_pdf(filename):
    """Handle PDF download requests"""
    try:
        logger.info(f"Download request for: {filename}")
        
        temp_dir = tempfile.gettempdir()
        safe_filename = secure_filename(filename.replace('/', '_')) + '.txt'
        temp_file = os.path.join(temp_dir, safe_filename)
        
        mock_content = f"""
DELHI HIGH COURT
Case Document: {filename}

This is a demonstration file. In a real implementation, 
this would be the actual PDF document from the court website.

Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(mock_content)
        
        return send_file(
            temp_file,
            as_attachment=True,
            download_name=safe_filename,
            mimetype='text/plain'
        )
        
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        return jsonify({'error': 'File not found or could not be downloaded'}), 404

@app.route('/history')
def query_history():
    """Display query history"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT case_type, case_number, filing_year, query_timestamp, status, id, is_blocked
            FROM queries
            ORDER BY query_timestamp DESC
            LIMIT 50
        ''')
        
        history = cursor.fetchall()
        conn.close()
        
        return render_template('history.html', history=history)
        
    except Exception as e:
        logger.error(f"Error fetching history: {str(e)}")
        return f"Error loading history: {str(e)}", 500

@app.route('/history/clear', methods=['POST'])
def clear_history():
    """Clear all search history"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM queries')
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/download/raw/<int:query_id>')
def download_raw_data(query_id):
    """Download raw response data for a query"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT raw_response FROM queries WHERE id = ?', (query_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return jsonify({'error': 'Query not found'}), 404
            
        # Create a temporary file
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, f'raw_response_{query_id}.txt')
        
        with open(temp_file, 'w') as f:
            f.write(result[0])
        
        return send_file(
            temp_file,
            as_attachment=True,
            download_name=f"raw_response_{query_id}.txt",
            mimetype='text/plain'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def log_query(case_type, case_number, filing_year, raw_response, status, parsed_data, is_blocked=False):
    """Log the query and response to database"""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO queries 
            (case_type, case_number, filing_year, raw_response, status, parsed_data, is_blocked)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            case_type, 
            case_number, 
            filing_year, 
            raw_response, 
            status, 
            json.dumps(parsed_data) if parsed_data else '{}',
            int(is_blocked)
        ))
        
        conn.commit()
        logger.info(f"Query logged: {case_type} {case_number}/{filing_year} - {status}")
    except Exception as e:
        logger.error(f"Error logging query: {str(e)}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    try:
        init_db()
        logger.info("Database initialized successfully")
        
        port = int(os.environ.get('PORT', 5000))
        debug = os.environ.get('DEBUG', 'True').lower() == 'true'
        
        logger.info(f"Starting server on port {port} with debug={debug}")
        print("\n" + "="*50)
        print("🏛️  COURT DATA FETCHER")
        print("="*50)
        print("⚠️  IMPORTANT NOTICE:")
        print("This application currently returns MOCK DATA because:")
        print("1. Delhi High Court website has CAPTCHA protection")
        print("2. Anti-bot measures prevent automated access")
        print("3. Real scraping requires manual intervention")
        print("\nTo get REAL data, you need to:")
        print("1. Manually visit: https://delhihighcourt.nic.in/app/get-case-type-status")
        print("2. Use CAPTCHA solving services")
        print("3. Implement manual verification steps")
        print("="*50)
        
        app.run(host='0.0.0.0', port=port, debug=debug)
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        raise