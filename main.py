# main.py
from flask import Flask, request, jsonify, redirect
import urllib.parse
import logging
import json
import sys
import time
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
try:
    load_dotenv()
except Exception as e:
    logging.warning(f"Failed to load .env file: {e}")

# Initialize Flask app
app = Flask(__name__)

# Configure structured logging
def setup_cloud_logging():
    """Configure logging for both local development and Cloud Run"""
    
    class JsonFormatter(logging.Formatter):
        def format(self, record):
            # Enhanced log entry with URL encoding details
            log_entry = {
                'severity': record.levelname,
                'message': record.getMessage(),
                'timestamp': self.formatTime(record),
                'original_url': getattr(record, 'original_url', None),
                'encoded_url': getattr(record, 'encoded_url', None),
                'final_url': getattr(record, 'final_url', None),
                'referrer': getattr(record, 'referrer', None),
                'processing_time_ms': getattr(record, 'processing_time_ms', None),
                'error_type': getattr(record, 'error_type', None),
                'error_message': getattr(record, 'error_message', None)
            }
            return json.dumps({k: v for k, v in log_entry.items() if v is not None})

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Set to DEBUG for more detailed logs
    logger.handlers = []
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    
    return logger

# Initialize the logger
logger = setup_cloud_logging()

# Configuration
class Config:
    """Configuration management for URL Proxy service."""
    
    # Class variables need to be defined before being used
    IS_PRODUCTION = os.getenv('FLASK_ENV') == 'production'
    DEFAULT_HOSTS = {
        'search.ebscohost.com',
        'www.proquest.com',
        'search.proquest.com',
        'link.gale.com',
        'go.gale.com'
    }
    
    # use IS_PRODUCTION in the VALID_HOSTS definition
    _env_hosts = os.getenv('VALID_HOSTS', '')
    VALID_HOSTS = set()
    if _env_hosts:
        for host in _env_hosts.split(','):
            if host.strip():
                if not (IS_PRODUCTION and 'localhost' in host):
                    VALID_HOSTS.add(host.strip())
    else:
        VALID_HOSTS = DEFAULT_HOSTS.copy()
    
    # OpenAthens configuration with validation
    try:
        OPENATHENS_PREFIXES = json.loads(os.getenv('OPENATHENS_PREFIXES', '{}'))
        if not OPENATHENS_PREFIXES:
            logger.warning(
                'No OpenAthens prefixes configured - falling back to default prefix',
                extra={
                    'config_status': 'missing_prefixes',
                    'fallback_prefix': 'https://go.openathens.net/redirector/OPEN-ATHENS-ID-1.edu' #replace OPEN-ATHENS-ID-1
                }
            )
    except json.JSONDecodeError as e:
        logger.error(
            'Failed to parse OPENATHENS_PREFIXES environment variable',
            extra={
                'error_type': 'json_decode_error',
                'error_message': str(e)
            }
        )
        OPENATHENS_PREFIXES = {}

    DEFAULT_OPENATHENS_PREFIX = 'https://go.openathens.net/redirector/OPEN-ATHENS-ID-1.edu' #replace OPEN-ATHENS-ID-1
    
    # Load valid referrers from environment variable
    VALID_REFERRERS = set(ref.strip() for ref in os.getenv('VALID_REFERRER', '').split(',') if ref.strip())
    
    # Add proxy domain to valid hosts
    PROXY_DOMAIN = os.getenv('PROXY_DOMAIN', '').strip('/')
    if PROXY_DOMAIN:
        VALID_HOSTS.add(PROXY_DOMAIN)

    @classmethod
    def get_openathens_prefix(cls, referrer):
        """Get OpenAthens prefix for given referrer with enhanced logging"""
        if not referrer:
            logger.info('No referrer provided - using default prefix')
            return cls.DEFAULT_OPENATHENS_PREFIX

        for ref_domain, prefix in cls.OPENATHENS_PREFIXES.items():
            if ref_domain in referrer:
                logger.info(
                    'Found matching OpenAthens prefix',
                    extra={
                        'referrer': referrer,
                        'prefix': prefix,
                        'ref_domain': ref_domain
                    }
                )
                return prefix

        logger.info(
            'No matching prefix found for referrer - using default',
            extra={
                'referrer': referrer,
                'default_prefix': cls.DEFAULT_OPENATHENS_PREFIX,
                'available_domains': list(cls.OPENATHENS_PREFIXES.keys())
            }
        )
        return cls.DEFAULT_OPENATHENS_PREFIX

def safe_decode_url(url):
    """Safely decode a URL that may have multiple layers of encoding"""
    if not url:
        raise ValueError("Empty URL provided")

    prev_url = None
    current_url = url
    decode_count = 0
    max_decodes = 5  # Prevent infinite loops
    
    while prev_url != current_url and decode_count < max_decodes:
        prev_url = current_url
        try:
            current_url = urllib.parse.unquote(prev_url)
            decode_count += 1
        except Exception as e:
            logger.error('URL decoding error', extra={
                'error_type': type(e).__name__,
                'url': url,
                'decode_count': decode_count
            })
            break
    
    return current_url

def strip_proxy_url(url):
    """
    Remove proxy prefix if present and extract the target URL.
    Enhanced to handle various proxy URL formats.
    """
    if not Config.PROXY_DOMAIN:
        return url
        
    patterns = [
        f"{Config.PROXY_DOMAIN}/login?url=",
        f"{Config.PROXY_DOMAIN}?url=",
        f"{Config.PROXY_DOMAIN}/",
        f"http://{Config.PROXY_DOMAIN}/",
        f"https://{Config.PROXY_DOMAIN}/"
    ]
    
    original_url = url
    for pattern in patterns:
        if pattern in url:
            parts = url.split(pattern)
            if len(parts) > 1:
                logger.debug('Stripped proxy URL', extra={
                    'original_url': original_url,
                    'stripped_url': parts[1],
                    'pattern_matched': pattern
                })
                return parts[1]
    
    return url

def extract_url_from_request(request_url):
    """Extract and process the URL from the full request URL with enhanced error handling"""
    try:
        # Log the raw request URL
        logger.debug('Processing raw request URL', extra={'raw_url': request_url})
        
        parsed = urllib.parse.urlparse(request_url)
        raw_query = parsed.query
        
        url_start = raw_query.find("url=")
        if url_start == -1:
            raise ValueError("No URL parameter found in request")
            
        encoded_url = raw_query[url_start + 4:]
        decoded_url = safe_decode_url(encoded_url)
        
        logger.debug('URL extracted successfully', extra={
            'raw_url': request_url,
            'encoded_url': encoded_url,
            'decoded_url': decoded_url
        })
        
        return decoded_url
        
    except Exception as e:
        logger.error("URL extraction error", extra={
            'error_type': type(e).__name__,
            'request_url': request_url,
            'error_message': str(e)
        })
        raise

def verify_request(url, referrer=None):
    """Combined security checks with enhanced logging"""
    try:
        if not url:
            logger.warning('Empty URL provided')
            return False
        
        parsed_url = urllib.parse.urlparse(url)
        if parsed_url.netloc not in Config.VALID_HOSTS:
            logger.warning('Invalid host detected', extra={
                'target_url': parsed_url.netloc,
                'valid_hosts': list(Config.VALID_HOSTS)
            })
            return False
            
        if Config.VALID_REFERRERS and referrer:
            if not any(ref in referrer for ref in Config.VALID_REFERRERS):
                logger.warning('Invalid referrer', extra={
                    'referrer': referrer,
                    'valid_referrers': list(Config.VALID_REFERRERS)
                })
                return False
            
        return True
        
    except Exception as e:
        logger.error('Request verification error', extra={
            'error_type': type(e).__name__,
            'url': url,
            'referrer': referrer
        })
        return False

@app.route('/encode', methods=['GET'])
def encode_url():
    try:
        start_time = time.time()
        
        # Log incoming request
        logger.debug('Received encoding request', extra={
            'original_url': request.url,
            'referrer': request.referrer
        })
        
        referrer = request.referrer
        
        try:
            target_url = strip_proxy_url(extract_url_from_request(request.url))
            logger.info('URL extracted', extra={
                'original_url': target_url
            })
        except ValueError as e:
            logger.error('URL extraction failed', extra={
                'error_type': type(e).__name__,
                'error_message': str(e)
            })
            return jsonify({'error': str(e)}), 400
        
        if not verify_request(target_url, referrer):
            logger.error('URL validation failed', extra={
                'original_url': target_url,
                'referrer': referrer
            })
            return jsonify({'error': 'Invalid request parameters'}), 403

        try:
            # Log the URL at each stage of processing
            encoded_url = urllib.parse.quote(target_url, safe='')
            openathens_prefix = Config.get_openathens_prefix(referrer)
            final_url = f"{openathens_prefix}?url={encoded_url}"
            
            processing_time = time.time() - start_time
            logger.info('URL processing complete', extra={
                'processing_time_ms': round(processing_time * 1000),
                'original_url': target_url,
                'encoded_url': encoded_url,
                'openathens_prefix': openathens_prefix,
                'final_url': final_url,
                'referrer': referrer
            })
            
            return redirect(final_url, code=302)
            
        except Exception as e:
            logger.error('URL encoding error', extra={
                'error_type': type(e).__name__,
                'error_message': str(e),
                'original_url': target_url
            })
            return jsonify({'error': str(e)}), 400
            
    except Exception as e:
        logger.error('Unexpected error', extra={
            'error_type': type(e).__name__,
            'error_message': str(e)
        })
        return jsonify({'error': 'Processing error'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Enhanced health check endpoint for Cloud Run"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'environment': os.getenv('FLASK_ENV', 'production'),
        'config_status': {
            'openathens_prefixes_configured': bool(Config.OPENATHENS_PREFIXES),
            'valid_hosts': list(Config.VALID_HOSTS),
            'valid_referrers': list(Config.VALID_REFERRERS),
            'proxy_domain': Config.PROXY_DOMAIN
        }
    }), 200

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Enhanced startup logging
    logger.info('Starting URL Proxy service', extra={
        'port': port,
        'debug_mode': debug_mode,
        'environment': os.getenv('FLASK_ENV', 'production'),
        'openathens_prefixes_configured': bool(Config.OPENATHENS_PREFIXES),
        'valid_hosts': list(Config.VALID_HOSTS),
        'valid_referrers': list(Config.VALID_REFERRERS),
        'proxy_domain': Config.PROXY_DOMAIN
    })
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug_mode
    )
