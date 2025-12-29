# Motorcycle Specifications Implementation Summary

## Backend Changes (FastAPI)

### 1. Updated SQL Query (`app/apps/cms/router.py`)
- Added `LEFT JOIN` to `motorcycle_specifications` table
- Added `description` field from `motorcycles` table
- Added all specification fields from `motorcycle_specifications` table

### 2. Updated Technical Specs Building
- Replaced hardcoded defaults with actual database values
- Added support for both snake_case and camelCase field names for backward compatibility
- Row indices mapping:
  - 0-7: Basic motorcycle fields (id, model, price, color, year, inner_brand_model, brand_name, review_video_url)
  - 8: description
  - 9-18: Technical specs (engine, displacement, bore_x_stroke, power, torque, starting_system, fuel_capacity, transmission, cooling, ignition)
  - 19-25: Chassis specs (frame, front_suspension, rear_suspension, front_brake, rear_brake, front_tire, rear_tire)
  - 26-32: Dimensions (weight, length, width, height, wheelbase, seat_height, ground_clearance)

### 3. Updated Schema (`app/apps/cms/schemas.py`)
- Added `description: Optional[str] = None` to `MotorcycleCardItem`

## Frontend Changes (Nuxt/Vue)

### 1. Updated Specification Tables
- Added support for new fields:
  - `displacement` (Cilindrada)
  - `bore_x_stroke` (Diámetro x carrera)
  - `starting_system` (Arranque)
- Updated all fields to support both snake_case and camelCase naming

### 2. Updated Computed Properties
- `hasTechnicalSpecs`: Now checks for all new technical fields
- `hasChassisSpecs`: Now checks both snake_case and camelCase variants
- `hasDimensionsSpecs`: Now checks both snake_case and camelCase variants

### 3. Field Display Support
All specification fields now support both naming conventions:
- `front_suspension` / `frontSuspension`
- `rear_suspension` / `rearSuspension`
- `front_brake` / `frontBrake`
- `rear_brake` / `rearBrake`
- `front_tire` / `frontTire`
- `rear_tire` / `rearTire`
- `seat_height` / `seatHeight`
- `ground_clearance` / `groundClearance`
- `fuel_capacity` / `fuelCapacity`

## API Response Structure

The endpoint `/cms/marketplace/motorcycle/{motorcycle_id}` now returns:

```json
{
  "id": 6,
  "image": "...",
  "hero_image": "...",
  "name": "Brand Model",
  "price": "$XX,XXX",
  "colors": ["Color1", "Color2"],
  "description": "Motorcycle description text...",
  "technical": {
    "engine": "Blue Core, 4 tiempos...",
    "displacement": "125 cc",
    "bore_x_stroke": "52.4 mm x 57.9 mm",
    "power": "6.0 kW a 6500 rpm",
    "torque": "9.7 NM a 5000 rpm",
    "starting_system": "Eléctrico y pedal",
    "fuel_capacity": "5.2 L",
    "fuelCapacity": "5.2 L",
    "transmission": "Automática, CVT",
    "cooling": "Enfriado por aire",
    "front_suspension": "Horquilla telescópica",
    "frontSuspension": "Horquilla telescópica",
    "rear_suspension": "Basculante",
    "rearSuspension": "Basculante",
    "front_brake": "Disco Hidráulico con UBS",
    "frontBrake": "Disco Hidráulico con UBS",
    "rear_brake": "Tambor",
    "rearBrake": "Tambor",
    "front_tire": "90/90-12",
    "frontTire": "90/90-12",
    "rear_tire": "110/90-10",
    "rearTire": "110/90-10",
    "weight": "99 kg",
    "length": "1,880 mm",
    "width": "685 mm",
    "height": "1,190 mm",
    "wheelbase": "1,280 mm",
    "seat_height": "780 mm",
    "seatHeight": "780 mm",
    "ground_clearance": "145 mm",
    "groundClearance": "145 mm"
  },
  "images": [...]
}
```

## Testing Checklist

- [ ] Verify motorcycle ID 6 specifications are returned correctly
- [ ] Check that description field displays in frontend
- [ ] Verify all technical specifications display in tables
- [ ] Check that chassis specifications display correctly
- [ ] Verify dimensions display properly
- [ ] Test with motorcycles that don't have specifications (should show defaults)
- [ ] Test with motorcycles that have partial specifications

## Next Steps

1. Run the migration on the database (if not already done)
2. Insert specifications for motorcycle ID 6 using the provided SQL script
3. Test the endpoint: `GET /cms/marketplace/motorcycle/6`
4. Verify frontend displays all data correctly

