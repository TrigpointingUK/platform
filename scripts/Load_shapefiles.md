# Populating area tables

## Setup

```bash
# Get credentials into the environment
eval $(aws secretsmanager get-secret-value --region eu-west-1 --secret-id fastapi-staging-postgres-credentials --query SecretString --output text | jq -r '"export PG_HOST=\(.host) PG_USER=\(.username) PG_PASS=\(.password)"')

```

```sql
INSERT INTO area_type (id, code, name, description, source_url) VALUES
(1, 'historic_county', 'Historic County', 'Historic county boundaries definition A', 'https://wikishire.co.uk/lookup/'),
(2, 'admin_county', 'Administrative Boundary', 'Counties and Unitary Authorities (December 2024)', 'https://geoportal.statistics.gov.uk/');
(3, 'country', 'Country', 'Countries', '{"https://geoportal.statistics.gov.uk/datasets/8295b10303ce46c982f62af3733b9405_0/explore?location=52.116418%2C3.647172%2C5.03", "https://simplemaps.com/gis/country/ie#all"}');


INSERT INTO area_type (id, code, name, description, source_url) VALUES
(4, 'os_explorer', 'OS Explorer', 'Ordnance Survey Explorer maps 1:25k', 'https://shop.ordnancesurvey.co.uk/'),
(5, 'os_landranger', 'OS Landranger', 'Ordnance Survey Landranger maps 1:50k', 'https://shop.ordnancesurvey.co.uk/');
```


## Historic counties

```bash

ogrinfo -so GBIDefinitionA.shp
ogrinfo -so GBIDefinitionA.shp GBIDefinitionA

ogr2ogr -f "PostgreSQL" \
  "PG:host=localhost port=5433 dbname=tuk_staging user=$PG_USER password=$PG_PASS" \
  ~/Trigpointing/Data/GBIDefinitionA/GBIDefinitionA.shp \
  -nln area_staging_gbi \
  -nlt PROMOTE_TO_MULTI \
  -t_srs EPSG:4326 \
  -lco GEOMETRY_NAME=boundary \
  -overwrite
```

```sql
INSERT INTO area (area_type_id, code, name, boundary, properties)
SELECT 
    1 AS area_type_id,
    hcs_code AS code,
    name AS name,
    boundary,
    jsonb_build_object(
        'county', county,
        'abbr', abbr,
        'hcs_number', hcs_number,
        'hcs_code', hcs_code
    )::text AS properties
FROM area_staging_gbi;

```

## Admin Counties and Unitary Authorities

```bash

ogrinfo -so ~/Trigpointing/Data/Counties_and_Unitary_Authorities_December_2024_Boundaries_UK_BFE_5487825209569118971/CTYUA_DEC_2024_UK_BFE.shp CTYUA_DEC_2024_UK_BFE

ogr2ogr -f "PostgreSQL" \
  "PG:host=localhost port=5433 dbname=tuk_staging user=$PG_USER password=$PG_PASS" \
  ~/Trigpointing/Data/Counties_and_Unitary_Authorities_December_2024_Boundaries_UK_BFE_5487825209569118971/CTYUA_DEC_2024_UK_BFE.shp \
  -nln area_staging_ctyua \
  -nlt PROMOTE_TO_MULTI \
  -t_srs EPSG:4326 \
  -lco GEOMETRY_NAME=boundary \
  -overwrite \
  -sql "SELECT CTYUA24CD, CTYUA24NM, CTYUA24NMW, GlobalID FROM CTYUA_DEC_2024_UK_BFE"
```

```sql
INSERT INTO area (area_type_id, code, name, boundary, properties)
SELECT 
    2 AS area_type_id,
    CTYUA24CD AS code,
    CTYUA24NM AS name,
    boundary,
    jsonb_build_object(
        'welsh_name', CTYUA24NMW,
        'uuid', GlobalID
    )::text AS properties
FROM area_staging_ctyua;
```


## Countries

```bash
ogr2ogr -f "PostgreSQL" \
  "PG:host=localhost port=5433 dbname=tuk_staging user=$PG_USER password=$PG_PASS" \
  ~/Trigpointing/Data/Countries_December_2023_Boundaries_UK_BFE_5732326143658497071/CTRY_DEC_2023_UK_BFE.shp \
  -nln area_staging_ctry \
  -nlt PROMOTE_TO_MULTI \
  -t_srs EPSG:4326 \
  -lco GEOMETRY_NAME=boundary \
  -overwrite \
  -sql "SELECT CTRY23CD, CTRY23NM, CTRY23NMW, GlobalID FROM CTRY_DEC_2023_UK_BFE"
```

```sql
INSERT INTO area (area_type_id, code, name, boundary, properties)
SELECT 
    3 AS area_type_id,
    CTRY23CD AS code,
    CTRY23NM AS name,
    boundary,
    jsonb_build_object(
        'welsh_name', CTRY23NMW,
        'uuid', GlobalID
    )::text AS properties
FROM area_staging_ctry;
```


```bash
ogr2ogr -f "PostgreSQL" \
  "PG:host=localhost port=5433 dbname=tuk_staging user=$PG_USER password=$PG_PASS" \
  ~/Trigpointing/Data/Countries_Ireland/ie.shp \
  -nln area_staging_ctryie \
  -nlt PROMOTE_TO_MULTI \
  -t_srs EPSG:4326 \
  -lco GEOMETRY_NAME=boundary \
  -overwrite 
```

```sql
INSERT INTO area (area_type_id, code, name, boundary, properties)
SELECT 
    3 AS area_type_id,
    id AS code,
    name AS name,
    boundary,
    jsonb_build_object(
        'source', source
    )::text AS properties
FROM area_staging_ctryie;
```

## Sheets

```bash
ogr2ogr -f "PostgreSQL" \
  "PG:host=localhost port=5433 dbname=tuk_staging user=$PG_USER password=$PG_PASS" \
  /home/ianh/Trigpointing/Data/OS_maps_fixed.json \
  -nln area_staging_os_maps \
  -nlt PROMOTE_TO_MULTI \
  -s_srs EPSG:27700 \
  -t_srs EPSG:4326 \
  -lco GEOMETRY_NAME=boundary \
  -overwrite

```

```sql
INSERT INTO area (area_type_id, code, name, boundary, properties)
SELECT 
    4 AS area_type_id,
    sheet AS code,
    title AS name,
    boundary,
    jsonb_build_object(
        'number', number,
        'title', title,
        'subtitle', sub_title
    )::text AS properties
FROM area_staging_os_maps
WHERE series='Explorer';


INSERT INTO area (area_type_id, code, name, boundary, properties)
SELECT 
    5 AS area_type_id,
    sheet AS code,
    title AS name,
    boundary,
    jsonb_build_object(
        'number', number,
        'title', title,
        'subtitle', sub_title
    )::text AS properties
FROM area_staging_os_maps
WHERE series='Landranger';

```

## Ceremonial counties

```sql
INSERT INTO area_type (id, code, name, description, source_url) VALUES
(6, 'ceremonial_county', 'Ceremonial County', 'GB Ceremonial Counties', 'https://covid19.esriuk.com/datasets/esriukcontent::ceremonial-counties-1/explore?location=50.104165%2C0.316975%2C5.42');
```

```bash
ogr2ogr -f "PostgreSQL" \
  "PG:host=localhost port=5433 dbname=tuk_staging user=$PG_USER password=$PG_PASS" \
  ~/Trigpointing/Data/Ceremonial_counties-OS_Boundaryline_7144299620154118672/Ceremonial_counties.shp \
  -nln area_staging_ceremonial \
  -nlt PROMOTE_TO_MULTI \
  -t_srs EPSG:4326 \
  -lco GEOMETRY_NAME=boundary \
  -overwrite

```

```sql
INSERT INTO area (area_type_id, name, boundary)
SELECT 
    6 AS area_type_id,
    name AS name,
    boundary
FROM area_staging_ceremonial;
```

```bash
# Export from staging (includes id column)
psql -h localhost -p 5433 -U fastapi_staging -d tuk_staging \
  -c "\copy (SELECT id, area_type_id, code, name, ST_AsText(boundary) AS boundary, parent_id, properties FROM area WHERE area_type_id = 6) TO '/tmp/area_type_6.csv' WITH CSV HEADER"

# Import to production
psql -h localhost -p 5433 -U fastapi_production -d tuk_production \
  -c "\copy area(id, area_type_id, code, name, boundary, parent_id, properties) FROM '/tmp/area_type_6.csv' WITH CSV HEADER"

# Fix the sequence after import
psql -h localhost -p 5433 -U fastapi_production -d tuk_production \
  -c "SELECT setval('area_id_seq', (SELECT COALESCE(MAX(id), 1) FROM area));"

```


