# Endpoint Migration Summary

This document summarizes the endpoints that have been migrated from `LoanCalculator2-backend` (Flask) to `fastapi-migration` (FastAPI) for the onCreditWeb flow implementation.

## Migrated Endpoints

### 1. Store Selection Endpoints

#### `/api/advisor/get_stores` (GET)
- **Status**: ✅ Already exists in `fastapi-migration/app/apps/advisor/router.py`
- **Description**: Fetches stores with flexible filtering (by brand, holding, etc.)
- **Frontend Usage**: `nuxt-quasar-migration/pages/confirm-store.vue`
- **Query Parameters**:
  - `brand` (optional): Filter by brand name
  - `holding` (optional): Filter by holding (Ferbel, Sfera)
  - `active` (optional): Filter by active status (default: true)
- **Response**: Returns list of stores with coordinates, brand info, etc.

#### `/api/advisor/get_next_user` (GET)
- **Status**: ✅ Already exists in `fastapi-migration/app/apps/advisor/router.py`
- **Description**: Gets the next available advisor for a store based on rotation logic
- **Query Parameters**:
  - `store_id` (required): ID of the store
  - `client_email` (required): Email of the client
  - `client_phone` (required): Phone number of the client
- **Response**: Returns advisor details

### 2. Client Validation Endpoints

#### `/api/client/validate_phone` (GET)
- **Status**: ✅ Already exists in `fastapi-migration/app/apps/client/router.py`
- **Description**: Validates a client by phone and email
- **Frontend Usage**: `nuxt-quasar-migration/stores/clientStore.js` → `validatePhoneAndEmail()`
- **Query Parameters**:
  - `phone` (required): Phone number
  - `email` (required): Email address
  - `simply_validation` (optional): Boolean for simple validation
- **Response**: Returns validation status, type, and clue if mismatch

#### `/api/client/validate_client` (GET)
- **Status**: ✅ Already exists in `fastapi-migration/app/apps/client/router.py`
- **Description**: Retrieves a client by email and phone number
- **Frontend Usage**: `nuxt-quasar-migration/stores/clientStore.js` → `getClient()`
- **Query Parameters**:
  - `email` (required): Email address
  - `phone` (required): Phone number
- **Response**: Returns client data, report, files, id, id_details, has_purchases

### 3. Client Registration Endpoints

#### `/api/loan/add_client_without_report` (POST)
- **Status**: ✅ **NEWLY MIGRATED** in `fastapi-migration/app/apps/loan/router.py`
- **Description**: Adds a new client without a report, creates associated Report and Solicitud
- **Frontend Usage**: `nuxt-quasar-migration/stores/clientStore.js` → `registerClientWithoutReport()`
- **Request Body**:
  ```json
  {
    "phone": "string",
    "email": "string",
    "id_motorcycle": int,
    "user_id": int,
    "payment_method": "string",
    "preferred_store_id": int (optional),
    "time_to_buy_motorcycle": "string" (optional),
    "registration_process": "string" (optional),
    "registration_mode": "string" (optional),
    "curp": "string" (optional),
    "name": "string" (optional, required if no CURP),
    "first_last_name": "string" (optional, required if no CURP),
    "second_last_name": "string" (optional),
    "second_name": "string" (optional)
  }
  ```
- **Response**:
  ```json
  {
    "message": "Client and solicitud created successfully",
    "client_id": int,
    "solicitud_id": int
  }
  ```
- **Notes**:
  - CURP integration with Kiban API is marked as TODO (not yet implemented)
  - Email notifications are marked as TODO (requires email utility migration)

## Frontend Updates

### Updated API Paths

All frontend API calls have been updated to use the `/api` prefix:

1. **confirm-store.vue**:
   - `/get_stores` → `/api/advisor/get_stores`

2. **clientStore.js**:
   - `/client/validate_phone` → `/api/client/validate_phone`
   - `/client/validate_client` → `/api/client/validate_client`
   - `/add_client_without_report` → `/api/loan/add_client_without_report`

## Data Flow

1. **Motorcycle Selection** → Saved to `solicitudStore` (localStorage)
2. **Quote Generation** → Quote params saved to `solicitudStore`
3. **Store Selection** → Store ID saved to `solicitudStore`
4. **Client Validation** → Client validated/registered
5. **Client Registration** → Creates client, report, and solicitud via `/api/loan/add_client_without_report`

## TODO / Future Work

1. **Kiban API Integration**: 
   - CURP data fetching in `/add_client_without_report`
   - RFC generation
   - Credit report queries

2. **Email Notifications**:
   - Client registration notifications
   - Solicitud creation notifications

3. **Additional Endpoints** (if needed):
   - `/api/client/get_carrier` - Get carrier from phone number
   - `/api/client/get_neighborhoods/{zip_code}` - Get neighborhoods by ZIP code
   - Other client utility endpoints

## Testing Checklist

- [ ] Test `/api/advisor/get_stores` with brand filter
- [ ] Test `/api/advisor/get_next_user` with store_id, email, phone
- [ ] Test `/api/client/validate_phone` with valid/invalid combinations
- [ ] Test `/api/client/validate_client` with existing client
- [ ] Test `/api/loan/add_client_without_report` with new client
- [ ] Test `/api/loan/add_client_without_report` with existing client (should update)
- [ ] Verify localStorage persistence in frontend
- [ ] Test complete flow: quote → store → validation → registration

