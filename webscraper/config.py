import os


class Config:
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-change-in-production'
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'

    # Scraping settings
    REQUEST_TIMEOUT = int(os.environ.get('REQUEST_TIMEOUT', '10'))
    MAX_SCRAPES_PER_HOUR = int(os.environ.get('MAX_SCRAPES_PER_HOUR', '60'))

    # File settings
    CSV_FILENAME = os.environ.get('CSV_FILENAME', 'scraped_data.csv')