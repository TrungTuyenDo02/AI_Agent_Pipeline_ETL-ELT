WITH source_data AS (
    SELECT
        CAST(ssn AS VARCHAR) AS ssn,
        CAST(lastname AS VARCHAR) AS lastname,
        CAST(firstname AS VARCHAR) AS firstname,
        CAST(hiredate AS DATE) AS hiredate,
        CAST(REPLACE(REPLACE(salary, 'US$', ''), ',', '') AS DECIMAL(18, 2)) AS salary_amount,
        CAST(gender AS VARCHAR) AS gender,
        NULLIF(TRIM(CAST(performance AS VARCHAR)), '') AS performance,
        CAST(positionID AS BIGINT) AS position_id,
        CAST(locationID AS BIGINT) AS location_id
    FROM {{ source('raw', 'employee') }}
)
SELECT
    ssn,
    lastname,
    firstname,
    hiredate,
    salary_amount,
    gender,
    performance,
    position_id,
    location_id
FROM source_data
