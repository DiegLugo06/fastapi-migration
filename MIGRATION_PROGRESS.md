# FastAPI Migration Progress

## Completed Modules

### ✅ Authentication Module (`app/apps/authentication/`)
- **Models**: `User` model migrated to SQLModel
- **Schemas**: All request/response schemas created (Login, Refresh, Signup, etc.)
- **Router**: All endpoints migrated:
  - `POST /api/auth/login` - User login
  - `POST /api/auth/refresh` - Refresh access token
  - `POST /api/auth/signup` - User signup (requires admin role)
  - `POST /api/auth/reset_password` - Reset password
  - `POST /api/auth/send_email_password_reset` - Send password reset email
  - `POST /api/auth/validate-refresh` - Validate refresh token
  - `POST /api/auth/login-portal` - Portal login with cookies
  - `POST /api/auth/refresh-portal` - Portal refresh with cookies
  - `POST /api/auth/validate-portal` - Validate portal tokens
  - `POST /api/auth/logout-portal` - Logout and clear cookies
- **Dependencies**: 
  - `get_current_user` - Authentication dependency
  - `get_current_user_optional` - Optional authentication
  - `retry_with_exponential_backoff` - Retry utility
- **Utils**: Supabase client utility

## Pending Modules

### ⏳ Advisor Module (`app/apps/advisor/`)
**Endpoints to migrate:**
- `GET /get_user` - Get user information
- `GET /get_stores` - Get stores with filtering
- `PUT /update_user` - Update user information
- `GET /get_advisor_details/<advisor_id>` - Get advisor details
- `POST /sucursales` - Create sucursal
- `GET /get_next_user` - Get next advisor by rotation
- `GET /get_next_finva_user` - Get next finva advisor
- `GET /get_next_finva_agent_zae` - Get next finva agent zae

**Utils to migrate:**
- `_fetch_banks.py`
- `_fetch_store.py`
- `_fetch_user.py`
- `_format_advisor_response.py`
- `_get_next_advisor.py`

### ⏳ Client Module (`app/apps/client/`)
**Endpoints to migrate:**
- `POST /cliente` - Create client
- `GET /cliente/<id>` - Get client
- `PUT /cliente/<cliente_id>` - Update client
- `POST /generate_rfc` - Generate RFC
- `GET /validate_client` - Validate client
- `GET /validate_phone` - Validate phone
- `GET /get_neighborhoods/<zip_code>` - Get neighborhoods
- `POST /extract-validation-ine` - Extract INE validation
- `POST /validate-lista-nominal` - Validate INE by Kiban
- `POST /validate-curp` - Validate CURP
- `POST /generate-curp` - Generate CURP
- `POST /unknown-client` - Register unknown client
- `POST /validate-ine-tuidentidad` - Validate INE with TuIdentidad
- `POST /validate-credential-complete` - Complete credential validation
- `POST /send-redirect-url` - Send redirect URL
- `POST /notify-validation-failed` - Notify validation failure
- `GET /file-status/<client_id>` - Get file status
- `PUT /file-status/<cliente_id>` - Update file status
- `POST /notify-files-uploaded` - Notify files uploaded
- `GET /files/<client_id>` - Get client files
- `POST /document/<client_id>` - Upload document
- `GET /document/<client_id>/download` - Download document
- `PUT /document/<client_id>/status` - Update document status
- `POST /validate-ine-manually` - Validate INE manually
- `GET /unknown-client/<phone>` - Get unknown client

**Utils to migrate:**
- `_data_validators.py`
- `_send_client_notification.py`
- `_transform_curp_responses.py`
- `convert_img_base64.py`
- `ine_validation_utils.py`
- `register_deal_hubspot.py`
- `send_email_to_user.py`
- `sync_crm_client.py`
- `validate_img.py`
- `validate_ine_ocr_info.py`
- `validate_ocr_data.py`
- `validation_ine_functions.py`

### ⏳ Product Module (`app/apps/product/`)
**Endpoints to migrate:**
- `GET /product/motorcycle_models` - Get motorcycle models
- `POST /product/create_discount` - Create discount
- `GET /product/decode_discount_hash/<discount_hash>` - Decode discount hash
- `GET /product/get_brand_by_id/<brand_id>` - Get brand by ID
- `GET /product/health` - Health check
- `GET /extract-technical-sheet/<motorcycle_id>` - Extract technical sheet
- `GET /products` - Get motorcycles catalog

**Utils to migrate:**
- `_get_technical_sheet_from_bucket.py`
- `decryption_functions.py`

### ⏳ Quote Module (`app/apps/quote/`)
**Endpoints to migrate:**
- `POST /quote` - Generate bank quotes
- `POST /get_bank_quote` - Get bank quote via web scraping
- `POST /qualitas-emision` - Qualitas emission
- `POST /lista-tarifas` - List tariffs
- `POST /get_qualitas_quote` - Get Qualitas quote

**Utils to migrate:**
- `banregio_quote.py`
- `bbva_quote.py`
- `hey_quote.py`
- `santander_quote.py`

**Services to migrate:**
- Qualitas service (if exists)

### ⏳ Loan Module (`app/apps/loan/`)
**Endpoints to migrate:**
- Check `app/loan/routes.py` for all endpoints (file is too large to read at once)

**Utils to migrate:**
- All files in `app/loan/utils/` directory

## Next Steps

1. **Fix Authentication Router Issues:**
   - Fix `reset_password` endpoint to properly extract headers
   - Add role-based permission checks
   - Test all endpoints

2. **Migrate Advisor Module:**
   - Create models (if needed)
   - Create schemas
   - Create router with all endpoints
   - Migrate utility functions

3. **Migrate Client Module:**
   - Create models (Cliente, FileStatus, IncomeProofDocument, Report, ClientesUnknown)
   - Create schemas
   - Create router with all endpoints
   - Migrate utility functions

4. **Migrate Product Module:**
   - Create models (MotorcycleBrand, Motorcycles, MotorcycleQualitasAmis, Discounts, StaticQuotes)
   - Create schemas
   - Create router with all endpoints
   - Migrate utility functions

5. **Migrate Quote Module:**
   - Create models (Banco, FinancingOption, BankOfferRequirement, Sucursal)
   - Create schemas
   - Create router with all endpoints
   - Migrate utility functions and services

6. **Migrate Loan Module:**
   - Read and understand all endpoints
   - Create models
   - Create schemas
   - Create router
   - Migrate utility functions

## Notes

- All modules need to use async database operations
- All Flask decorators need to be converted to FastAPI dependencies
- All SQLAlchemy queries need to be converted to async SQLModel queries
- Cookie handling in FastAPI is different from Flask - need to use Response object
- File uploads need to use FastAPI's `UploadFile` instead of Flask's `request.files`

