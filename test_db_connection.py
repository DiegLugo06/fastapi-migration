"""
Diagnostic script to test database connection and SSL configuration
Run this to debug database connectivity issues
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import test_db_connection, async_engine
from app.config import DATABASE_URL, MODE, DB_SSL_CERT_PATH as CERT_PATH
import os
import ssl

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Run diagnostic tests"""
    print("=" * 60)
    print("Database Connection Diagnostic")
    print("=" * 60)
    print(f"\nMode: {MODE}")
    # Mask password in URL for security
    db_url_display = DATABASE_URL
    if "@" in db_url_display:
        parts = db_url_display.split("@")
        if ":" in parts[0]:
            user_pass = parts[0].split("://")[1] if "://" in parts[0] else parts[0]
            if ":" in user_pass:
                user, _ = user_pass.split(":", 1)
                db_url_display = db_url_display.replace(user_pass, f"{user}:***")
    print(f"Database URL: {db_url_display[:80]}...")
    
    # Check SSL certificate
    print(f"\nSSL Certificate Path: {CERT_PATH}")
    if os.path.exists(CERT_PATH):
        file_size = os.path.getsize(CERT_PATH)
        print(f"  ✓ Certificate file exists ({file_size} bytes)")
        try:
            with open(CERT_PATH, 'r') as f:
                content = f.read()
                print(f"  ✓ Certificate readable")
                print(f"  - First line: {content.split(chr(10))[0][:60]}...")
                print(f"  - Last line: {content.split(chr(10))[-1][:60]}...")
        except Exception as e:
            print(f"  ✗ Error reading certificate: {e}")
    else:
        print(f"  ✗ Certificate file NOT found")
    
    # Try to create SSL context (same as database.py does)
    print(f"\nSSL Configuration Test:")
    try:
        if os.path.exists(CERT_PATH) and os.path.getsize(CERT_PATH) > 0:
            test_ssl = ssl.create_default_context(cafile=CERT_PATH)
            test_ssl.check_hostname = False
            test_ssl.verify_mode = ssl.CERT_REQUIRED
            print(f"  ✓ SSL context can be created")
            print(f"  - Check hostname: {test_ssl.check_hostname}")
            print(f"  - Verify mode: {test_ssl.verify_mode}")
        else:
            print(f"  ✗ Cannot create SSL context (certificate missing/empty)")
    except Exception as e:
        print(f"  ✗ Error creating SSL context: {e}")
        import traceback
        traceback.print_exc()
    
    # Test connection
    print(f"\nTesting database connection...")
    print("-" * 60)
    try:
        success = await test_db_connection()
        if success:
            print("\n✓ Database connection successful!")
        else:
            print("\n✗ Database connection failed!")
    except Exception as e:
        print(f"\n✗ Error during connection test: {e}")
        import traceback
        traceback.print_exc()
    
    # Try to get engine info
    try:
        print(f"\nEngine Info:")
        pool = async_engine.pool
        print(f"  - Pool size: {pool.size()}")
        print(f"  - Checked out: {pool.checkedout()}")
    except Exception as e:
        print(f"  - Could not get pool info: {e}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

