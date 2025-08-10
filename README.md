# 🏛️ Court Data Fetcher & Mini-Dashboard

A web application for fetching and displaying case information from Indian courts with a focus on the Delhi High Court.
Live app link : https://court-data-fetcher-mini-dashboard-4307.onrender.com

## 📋 Table of Contents
- [Overview](#overview)
- [Court Selection](#court-selection)
- [Features](#features)
- [Architecture](#architecture)
- [CAPTCHA Strategy](#captcha-strategy)
- [Installation](#installation)
- [Environment Variables](#environment-variables)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Database Schema](#database-schema)
- [Limitations & Known Issues](#limitations--known-issues)
- [Future Enhancements](#future-enhancements)
- [Contributing](#contributing)
- [License](#license)

## 🎯 Overview

This application allows users to search for case information from Indian courts by entering case details (Case Type, Case Number, Filing Year). It attempts to scrape data from court websites and provides a clean interface to view case metadata, party information, hearing dates, and download court orders.

**⚠️ Important Notice**: Due to CAPTCHA protection on court websites, this application currently returns mock data for demonstration purposes. See the [CAPTCHA Strategy](#captcha-strategy) section for details on accessing real data.

## 🏛️ Court Selection

**Primary Target**: Delhi High Court (https://delhihighcourt.nic.in/)

**Reasoning**:
- Well-structured website with consistent case status URLs
- Comprehensive case information display
- Multiple case types supported
- Active court with recent cases for testing

**Supported Case Types**:
- WP(C) - Writ Petition (Civil)
- CRL.A. - Criminal Appeal
- FAO - First Appeal from Order
- CM - Civil Misc
- CRL.M.C. - Criminal Misc Case
- CRL.REV.P. - Criminal Revision Petition
- MAT.APP. - Mat Appeal
- RFA - Regular First Appeal
- CRL.M.A. - Criminal Misc Application
- W.P.(CRL.) - Writ Petition (Criminal)

## ✨ Features

### Core Functionality
- **Case Search**: Search by case type, number, and filing year
- **Data Extraction**: Parse parties' names, filing dates, hearing dates, case status
- **Order Management**: Display and download court orders/judgments
- **Query Logging**: All searches logged to database with timestamps
- **History Tracking**: View previous searches and results
- **Error Handling**: User-friendly error messages for various scenarios

### Technical Features
- **Headless Browser Automation**: Selenium WebDriver with Chrome
- **Anti-Detection Measures**: Random user agents, stealth options
- **Database Integration**: SQLite for query logging and case storage
- **PDF Handling**: Mock PDF generation for demonstration
- **Responsive UI**: Clean, mobile-friendly interface
- **Real-time Feedback**: Loading states and progress indicators

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Flask App     │    │   Database      │
│   (HTML/CSS/JS) │◄──►│   (Python)      │◄──►│   (SQLite)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │ DelhiHighCourt  │
                       │ RealScraper     │
                       │ (Selenium)      │
                       └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │ Court Website   │
                       │ (CAPTCHA        │
                       │  Protected)     │
                       └─────────────────┘
```

### Components
1. **Flask Web Application**: RESTful API endpoints and template rendering
2. **DelhiHighCourtRealScraper**: Selenium-based web scraping engine
3. **Database Layer**: SQLite for persistent storage
4. **Frontend**: HTML templates with JavaScript for dynamic interactions

## 🔒 CAPTCHA Strategy

### Current Implementation
The Delhi High Court website implements CAPTCHA protection to prevent automated access. Our current strategy includes:

#### Detection Methods
```python
def _captcha_detected(self):
    captcha_selectors = [
        "img[src*='captcha']",
        "img[alt*='captcha']", 
        "#captcha",
        ".captcha",
        "input[name*='captcha']",
        "canvas"
    ]
    
    # Check for CAPTCHA elements and keywords
    for selector in captcha_selectors:
        if self.driver.find_elements(By.CSS_SELECTOR, selector):
            return True
    return False
```

#### Workaround Options

1. **Manual Intervention Points**
   ```python
   # Pause execution for manual CAPTCHA solving
   input("Please solve CAPTCHA manually and press Enter...")
   ```

2. **CAPTCHA Solving Services** (Recommended for production)
   - [2captcha](https://2captcha.com/)
   - [Anti-Captcha](https://anti-captcha.com/)
   - [DeathByCaptcha](https://deathbycaptcha.com/)

3. **Hybrid Approach**
   - Automated form filling
   - Manual CAPTCHA verification
   - Continued automated processing

4. **Alternative Data Sources**
   - Official court APIs (if available)
   - RSS feeds or data dumps
   - Partnership with legal data providers

### Example Integration with 2captcha
```python
# This is not implemented but shows the approach
def solve_captcha_with_2captcha(self, captcha_image_base64):
    api_key = os.getenv('TWOCAPTCHA_API_KEY')
    # Submit captcha to 2captcha service
    # Wait for solution
    # Return solved captcha text
```

## 🚀 Installation

### Prerequisites
- Python 3.8+
- Chrome Browser
- ChromeDriver (automatically managed by selenium)
- Git

### Step-by-Step Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/surabhi-chandrakant/Court-Data-Fetcher-Mini-Dashboard.git
   cd court-data-fetcher
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux  
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Chrome and ChromeDriver**
   ```bash
   # ChromeDriver is automatically managed by selenium 4+
   # Just ensure Chrome browser is installed
   ```

5. **Setup Environment Variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

6. **Initialize Database**
   ```bash
   python -c "from app import init_db; init_db()"
   ```

7. **Run the Application**
   ```bash
   python app.py
   ```

### Docker Installation (Optional)

```dockerfile
FROM python:3.9-slim

# Install Chrome dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["python", "app.py"]
```

```bash
docker build -t court-data-fetcher .
docker run -p 5000:5000 court-data-fetcher
```

## 🔧 Environment Variables

Create a `.env` file in the project root:

```bash
# Flask Configuration
SECRET_KEY=your-secret-key-here
DEBUG=True
PORT=5000

# Database Configuration  
DATABASE_URL=sqlite:///court_data.db

# Optional: CAPTCHA Solving Service
TWOCAPTCHA_API_KEY=your-2captcha-api-key
ANTICAPTCHA_API_KEY=your-anticaptcha-api-key

# Optional: Proxy Configuration
HTTP_PROXY=http://proxy-server:port
HTTPS_PROXY=https://proxy-server:port

# Browser Configuration
HEADLESS_BROWSER=True
CHROME_BINARY_PATH=/usr/bin/google-chrome

# Logging
LOG_LEVEL=INFO
LOG_FILE=court_fetcher.log
```

### Required Environment Variables
- `SECRET_KEY`: Flask session secret key
- `PORT`: Application port (default: 5000)

### Optional Environment Variables
- `DEBUG`: Enable debug mode (default: True)
- `TWOCAPTCHA_API_KEY`: For automated CAPTCHA solving
- `HTTP_PROXY`/`HTTPS_PROXY`: For proxy usage
- `HEADLESS_BROWSER`: Run browser in headless mode

## 🎯 Usage

### Web Interface

1. **Access the Application**
   ```
   http://localhost:5000
   ```

2. **Search for a Case**
   - Select case type from dropdown
   - Enter case number (numeric)
   - Enter filing year (4-digit year)
   - Click "Search Case"

3. **View Results**
   - Case details displayed in formatted cards
   - Download available orders/judgments
   - View case history and status

4. **Check History**
   - Visit `/history` to see previous searches
   - Download raw responses for debugging

### Sample Test Cases

```json
{
  "case_type": "WP(C)",
  "case_number": "12345",
  "filing_year": "2023"
}

{
  "case_type": "CRL.A.",
  "case_number": "67890", 
  "filing_year": "2024"
}
```

## 🔌 API Endpoints

### POST /search
Search for case information

**Request Body:**
```json
{
  "case_type": "WP(C)",
  "case_number": "12345", 
  "filing_year": "2023"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "case_number": "WP(C) 12345/2023",
    "parties": {
      "petitioner": "John Doe",
      "respondent": "State of Delhi & Others"
    },
    "filing_date": "15/03/2023",
    "next_hearing_date": "25/12/2024", 
    "case_status": "Listed for hearing",
    "orders": [
      {
        "date": "20/11/2024",
        "order_type": "Order",
        "description": "Case adjourned to next date",
        "pdf_link": "/orders/WP(C)_12345_2023_order.pdf"
      }
    ]
  },
  "source": "mock_data"
}
```

### GET /history
Retrieve search history

### GET /download/<filename>
Download court order PDFs

### POST /history/clear
Clear all search history

## 🗃️ Database Schema

### queries Table
```sql
CREATE TABLE queries (
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
);
```

### case_data Table  
```sql
CREATE TABLE case_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_number TEXT NOT NULL,
    parties TEXT,
    filing_date TEXT,
    next_hearing_date TEXT,
    case_status TEXT,
    orders_count INTEGER DEFAULT 0,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## ⚠️ Limitations & Known Issues

### Current Limitations
1. **CAPTCHA Protection**: Delhi High Court website blocks automated access
2. **Mock Data**: Currently returns sample data for demonstration
3. **Single Court**: Only supports Delhi High Court structure
4. **Rate Limiting**: No built-in rate limiting for requests
5. **Error Recovery**: Limited retry mechanisms

### Known Issues
1. **Selenium Dependencies**: ChromeDriver version compatibility
2. **Memory Usage**: Headless browser can consume significant memory
3. **Session Management**: No session persistence across restarts
4. **PDF Downloads**: Currently generates mock PDFs

### Browser Compatibility
- **Chrome**: Full support with ChromeDriver
- **Firefox**: Not currently supported (but can be added)
- **Safari**: Not supported on Linux deployments

## 🚀 Future Enhancements

### Phase 1: Core Improvements
- [ ] Integrate CAPTCHA solving services
- [ ] Add support for multiple courts
- [ ] Implement proper PDF downloading
- [ ] Add rate limiting and request queuing
- [ ] Enhanced error handling and logging

### Phase 2: Advanced Features  
- [ ] Real-time case status monitoring
- [ ] Email notifications for case updates
- [ ] Bulk case processing
- [ ] Export to Excel/CSV formats
- [ ] Advanced search filters

### Phase 3: Production Ready
- [ ] User authentication and authorization
- [ ] API rate limiting and quotas
- [ ] Caching layer (Redis)
- [ ] Load balancing support
- [ ] Comprehensive monitoring and alerting

### Potential Integrations
- **Payment Gateway**: For premium features
- **SMS Notifications**: Case update alerts
- **Legal Databases**: Cross-reference with legal precedents
- **Calendar Integration**: Hearing date reminders
- **Document OCR**: Extract text from scanned orders

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. **Fork the Repository**
2. **Create Feature Branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Commit Changes**
   ```bash
   git commit -m 'Add amazing feature'
   ```
4. **Push to Branch** 
   ```bash
   git push origin feature/amazing-feature
   ```
5. **Open Pull Request**

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/

# Run linting
flake8 app.py

# Format code
black app.py
```

### Code Style
- Follow PEP 8 guidelines
- Add docstrings for all functions
- Include type hints where possible
- Write unit tests for new features

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2024 Court Data Fetcher

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 📞 Support

For questions or support:
- 🐛 **Issues**: [GitHub Issues](https://github.com/surabhi-chandrakant/Court-Data-Fetcher-Mini-Dashboard/issues)
- 📧 **Email**: support@courtdatafetcher.com
- 📖 **Documentation**: [Wiki](https://github.com/surabhi-chandrakant/Court-Data-Fetcher-Mini-Dashboard/wiki)

---

**⚖️ Legal Disclaimer**: This tool is for educational and research purposes. Users are responsible for complying with court website terms of service and applicable laws. Always respect robots.txt and rate limits when scraping public websites.
