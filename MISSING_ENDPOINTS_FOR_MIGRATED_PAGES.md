# Missing Endpoints for Migrated Pages

This document lists the endpoints that are **NOT IMPLEMENTED** in the FastAPI backend but are **REQUIRED** for the migrated pages (`id-validation.vue` and `curp-generator.vue`).

## Critical Missing Endpoints

### 1. `/api/client/validate-curp` (POST)
- **Status**: ❌ NOT IMPLEMENTED (Returns 501)
- **Location**: `app/apps/client/router.py:740-749`
- **Used by**: 
  - `id-validation.vue` - Manual CURP validation fallback
  - `curp-generator.vue` - CURP validation after generation
- **Expected Request Body**:
  ```json
  {
    "curp": "CURP_STRING"
  }
  ```
- **Expected Response**:
  ```json
  {
    "client_data": {
      "nombres": "...",
      "primerApellido": "...",
      "segundoApellido": "...",
      "sexo": "...",
      "fechaNacimiento": "...",
      "curp": "...",
      "entidad": "...",
      "rfc": "..."
    },
    "status": "FOUND" | "NOT_FOUND" | "NOT_VALID"
  }
  ```
- **Error Response Format** (when validation fails):
  ```json
  {
    "success": false,
    "message": "Error message"
  }
  ```

### 2. `/api/client/generate-curp` (POST)
- **Status**: ❌ NOT IMPLEMENTED (Returns 501)
- **Location**: `app/apps/client/router.py:752-761`
- **Used by**: `curp-generator.vue` - Generate CURP from user data
- **Expected Request Body**:
  ```json
  {
    "nombres": "Juan Carlos",
    "primerApellido": "Pérez",
    "segundoApellido": "García",
    "sexo": "H" | "M",
    "claveEntidad": "DF",
    "fechaNacimiento": "1990-01-15"
  }
  ```
- **Expected Response**:
  ```json
  {
    "client_data": {
      "nombres": "...",
      "primerApellido": "...",
      "segundoApellido": "...",
      "sexo": "...",
      "fechaNacimiento": "...",
      "curp": "...",
      "entidad": "...",
      "rfc": "..."
    },
    "curp": "CURP_STRING",
    "status": "FOUND" | "NOT_FOUND" | "NOT_VALID"
  }
  ```

### 3. `/api/client/validate-credential-complete` (POST)
- **Status**: ❌ NOT IMPLEMENTED (Returns 501)
- **Location**: `app/apps/client/router.py:776-785`
- **Used by**: `id-validation.vue` - Complete INE validation (automatic OCR + validation)
- **Query Parameters**: `validation_type=automatic|manual`
- **Expected Request** (automatic):
  - Content-Type: `multipart/form-data`
  - FormData with:
    - `image_front`: File
    - `image_back`: File
- **Expected Request** (manual):
  - Content-Type: `application/json`
  - Body with manual data
- **Expected Response**:
  ```json
  {
    "curp": "CURP_STRING",
    "front_info": {
      "data": {
        "parse_ocr": [...]
      }
    },
    "back_info": {
      "data": {
        "mrz": {
          "doc_number": "...",
          "first_optional": "..."
        }
      }
    },
    "validation_details": {
      "ine": {
        "is_valid": true|false
      },
      "curp": {
        "is_valid": true|false
      }
    },
    "validation_results": {
      "curp": {
        "data": {
          "nombres": "...",
          "primerApellido": "...",
          "segundoApellido": "...",
          "sexo": "...",
          "fechaNacimiento": "...",
          "curp": "...",
          "entidad": "...",
          "rfc": "..."
        }
      }
    },
    "rfc": "RFC_STRING",
    "id_number": "INE_NUMBER",
    "is_valid": true|false,
    "ine_validation_message": "...",
    "ine_validation_clave_mensaje": "...",
    "ine_validation_user_message": "..."
  }
  ```
- **Error Response** (422 for poor image quality):
  - Status: 422
  - Body: Error message

## Implemented Endpoints ✅

### `/api/client/upload` (POST)
- **Status**: ✅ IMPLEMENTED
- **Location**: `app/apps/client/router.py:845-973`
- **Used by**: Both pages for uploading INE images
- **Query Parameters**: `type=officialIdFrontClient|officialIdReverseClient|...`
- **FormData**:
  - `client_id`: int
  - `file_type`: string
  - `file`: File
  - `validated`: string ("true"|"false")

### `/api/client/cliente` (POST)
- **Status**: ✅ IMPLEMENTED
- **Location**: `app/apps/client/router.py:39-132`
- **Used by**: Both pages for client registration

### `/api/client/cliente/{id}` (PUT)
- **Status**: ✅ IMPLEMENTED
- **Location**: `app/apps/client/router.py:169-235`
- **Used by**: Both pages for client updates

### `/api/client/validate_client` (GET)
- **Status**: ✅ IMPLEMENTED
- **Location**: `app/apps/client/router.py:255-347`
- **Used by**: `curp-generator.vue` - Get client data after registration

## Endpoint Path Configuration ⚠️

**Current Setup**:
- Frontend axios baseURL: `config.public.FLASK_BACKEND_URL` (e.g., `http://localhost:5000` or `http://localhost:5000/api`)
- Frontend calls: `/client/validate-curp`, `/client/generate-curp`, etc.
- Backend router prefix: `/api/client` (from `main.py` line 76)

**Expected Full Paths**:
- If `FLASK_BACKEND_URL = http://localhost:5000/api`: 
  - Frontend calls `/client/validate-curp` → `http://localhost:5000/api/client/validate-curp` ✅ **MATCHES**
- If `FLASK_BACKEND_URL = http://localhost:5000`:
  - Frontend calls `/client/validate-curp` → `http://localhost:5000/client/validate-curp` ❌ **MISMATCH**
  - Backend expects: `http://localhost:5000/api/client/validate-curp`

**Solution**:
Ensure `FLASK_BACKEND_URL` includes `/api` suffix, OR update frontend to call `/api/client/...` paths.

**Note**: Comment in `clientStore.js:103` suggests baseURL already includes `/api`, so this should be fine if configured correctly.

## Implementation Priority

### High Priority (Required for pages to work)
1. ✅ `/api/client/validate-credential-complete` - Core functionality for id-validation page
2. ✅ `/api/client/validate-curp` - Required for manual CURP validation
3. ✅ `/api/client/generate-curp` - Required for curp-generator page

### Medium Priority (Nice to have)
- `/api/client/extract-validation-ine` - Alternative extraction method
- `/api/client/validate-lista-nominal` - Additional validation method

## External Service Dependencies

All three missing endpoints require integration with external services that need to be migrated:

### 1. CURP Validation/Generation Services
- **Primary**: Nobarium API (`nobarium_service`)
- **Fallback 1**: ValidaCurp API (`ValidaCurpAPIService`)
- **Fallback 2**: Verificamex API (`VerificamexService`)
- **Response Transformers**: 
  - `transform_nubarium_curp_response`
  - `transform_first_service_response`
  - `transform_second_service_response`
- **Error Mapping**: `get_curp_validation_message_mapping` (maps error codes to user-friendly messages)

### 2. INE Validation Services
- **OCR Services**:
  - **Primary**: Nobarium OCR (`process_ocr_with_nobarium`)
  - **Fallback**: Verificamex OCR (`process_ocr_parallel`)
- **INE Validation Services**:
  - **Primary**: Nobarium INE validation (`validate_ine_nobarium`)
  - **Fallback**: Verificamex INE validation (`validate_ine_verificamex`)
- **Utility Functions**:
  - `process_image_validation` - Validates and processes uploaded images
  - `convert_images_to_base64` - Converts images to base64
  - `validate_ocr_results` - Validates OCR extraction results
  - `extract_curp_from_nobarium` - Extracts CURP from Nobarium response
  - `prepare_validation_body_nobarium` - Prepares validation body for Nobarium
  - `prepare_validation_body` - Prepares validation body for Verificamex
  - `validate_curp_and_ine_parallel` - Validates CURP and INE in parallel
  - `prepare_combined_response` - Prepares final response

### 3. Required Utility Modules (from Flask backend)
- `app/client/utils/ine_validation_utils.py` - Main validation utilities
- `app/client/utils/_transform_curp_responses.py` - CURP response transformers
- `app/client/utils/validate_ine_ocr_info.py` - OCR validation utilities
- `app/extensions/nobarium.py` - Nobarium service extension
- `app/extensions/valida_curp.py` - ValidaCurp service extension
- `app/extensions/verificamex.py` - Verificamex service extension
- `app/portal/utils/_format_curp_responses.py` - Error message mapping

## Error Handling Requirements

The endpoints should handle these error cases:

### `/api/client/validate-curp`
- **400**: Invalid CURP format, mapped error codes (1, 2, 3, 5, -1)
- **422**: CURP not found in database
- **503**: All validation services unavailable
- **500**: Internal server error

**Error Response Format**:
```json
{
  "success": false,
  "message": "User-friendly error message",
  "error_code": "1",
  "original_message": "Original service error",
  "service": "primary|fallback|second_fallback",
  "curp": "CURP_STRING"
}
```

### `/api/client/generate-curp`
- **400**: Missing required fields, invalid data format
- **422**: Generated CURP not found or invalid
- **503**: Service unavailable
- **500**: Internal server error

### `/api/client/validate-credential-complete`
- **400**: Missing images or required fields
- **422**: Poor image quality, OCR extraction failed, validation failed
- **503**: All validation services unavailable
- **500**: Internal server error

**422 Response Format** (for poor image quality):
```json
{
  "error": "OCR validation failed",
  "details": {
    "front_info": {...},
    "back_info": {...}
  },
  "timing_metrics": {...}
}
```

## Implementation Priority

### High Priority (Required for pages to work)
1. ✅ `/api/client/validate-credential-complete` - Core functionality for id-validation page
   - Requires: OCR services (Nobarium/Verificamex), INE validation services
   - Most complex endpoint - handles parallel validation
   
2. ✅ `/api/client/validate-curp` - Required for manual CURP validation
   - Requires: CURP validation services (Nobarium/ValidaCurp/Verificamex)
   - Has fallback chain: Primary → Fallback 1 → Fallback 2
   
3. ✅ `/api/client/generate-curp` - Required for curp-generator page
   - Requires: CURP generation service (likely same as validation)
   - Simpler than validation endpoint

### Migration Steps

1. **Migrate External Service Extensions**:
   - Create FastAPI-compatible versions of:
     - `nobarium_service`
     - `ValidaCurpAPIService`
     - `VerificamexService`

2. **Migrate Utility Functions**:
   - Migrate all functions from `ine_validation_utils.py`
   - Migrate response transformers
   - Migrate error message mappers

3. **Implement Endpoints**:
   - Start with `/validate-curp` (simplest)
   - Then `/generate-curp`
   - Finally `/validate-credential-complete` (most complex)

4. **Testing**:
   - Test with real INE images
   - Test error scenarios (poor quality, invalid CURP, etc.)
   - Test fallback service chains

