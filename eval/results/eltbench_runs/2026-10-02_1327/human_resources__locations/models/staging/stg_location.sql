WITH source_data AS (
    SELECT
        CAST(locationID AS BIGINT) AS location_id,
        CAST(locationcity AS VARCHAR) AS location_city,
        CAST(address AS VARCHAR) AS address,
        CAST(state AS VARCHAR) AS state,
        CAST(zipcode AS BIGINT) AS zipcode,
        CAST(officephone AS VARCHAR) AS office_phone
    FROM {{ source('raw', 'location') }}
)
SELECT
    location_id,
    location_city,
    address,
    state,
    zipcode,
    office_phone
FROM source_data
