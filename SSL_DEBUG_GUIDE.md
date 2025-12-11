# SSL Configuration Debug Guide

## Changes Made

### 1. Enhanced SSL Configuration (`app/database.py`)

**Improvements:**
- ✅ Added comprehensive logging for SSL certificate loading
- ✅ Increased timeouts (30s for commands, 30s for pool) to accommodate SSL handshake
- ✅ Better error handling with detailed exception logging
- ✅ Added pool size configuration (5 initial, 10 overflow)
- ✅ Created `test_db_connection()` function for diagnostics

**Key Changes:**
- `command_timeout`: 10s → 30s (SSL handshake can be slow)
- `pool_timeout`: 10s → 30s (allows more time for SSL connections)
- Added logging at each step of SSL configuration

### 2. Diagnostic Script (`test_db_connection.py`)

A standalone script to test and diagnose database connectivity issues.

## How to Debug

### Step 1: Run the Diagnostic Script

```powershell
python test_db_connection.py
```

This will:
- Check if SSL certificate file exists and is readable
- Test SSL context creation
- Attempt a database connection
- Show detailed error messages

### Step 2: Check the Logs

When you start your FastAPI app, you should now see:
```
INFO - Loading SSL certificate from: C:\Users\...\db-ca.crt (1234 bytes)
INFO - SSL context created successfully
INFO - SSL enabled for database connections
INFO - Database engine created (mode: staging, SSL: enabled)
```

### Step 3: Common Issues and Solutions

#### Issue: "SSL certificate file not found"
**Solution:** Check that `DB_SSL_CERT` environment variable is set correctly

#### Issue: "SSL certificate file is empty"
**Solution:** The certificate content in `.env` might be malformed. Check the `DB_SSL_CERT` value.

#### Issue: "TimeoutError during SSL handshake"
**Possible causes:**
1. **Network/Firewall**: Database server might be blocking connections
2. **SSL Certificate Mismatch**: Certificate might not match the database server
3. **Database Server Unavailable**: Server might be down or unreachable

**Solutions:**
- Verify database URL is correct
- Check if Flask project can still connect (to rule out network issues)
- Try temporarily disabling SSL to test basic connectivity

#### Issue: "Failed to create SSL context"
**Solution:** Check Python's SSL library and certificate file format

## Testing Without SSL (Temporary)

If you need to test basic connectivity without SSL, you can temporarily modify `app/database.py`:

```python
# Temporarily disable SSL
# if ssl_config:
#     connect_args["ssl"] = ssl_config
#     logger.info("SSL enabled for database connections")
# else:
#     logger.warning("SSL not configured - database connections will be unencrypted")

# Force no SSL for testing
connect_args["ssl"] = False
logger.warning("SSL DISABLED FOR TESTING ONLY")
```

**⚠️ Remember to re-enable SSL before deploying to production!**

## Comparison with Flask Configuration

**Flask (psycopg2):**
```python
connect_args = {
    "sslmode": "verify-full",
    "sslrootcert": DB_SSL_CERT_PATH,
}
```

**FastAPI (asyncpg):**
```python
ssl_config = ssl.create_default_context(cafile=DB_SSL_CERT_PATH)
ssl_config.check_hostname = False
ssl_config.verify_mode = ssl.CERT_REQUIRED
connect_args["ssl"] = ssl_config
```

Both achieve the same result but use different APIs because:
- `psycopg2` uses connection string parameters
- `asyncpg` uses Python's `ssl.SSLContext` object

## Next Steps

1. Run `python test_db_connection.py` to see detailed diagnostics
2. Check the application logs when starting the server
3. Compare the SSL certificate path and content with your Flask project
4. If issues persist, try the temporary SSL disable to isolate the problem

