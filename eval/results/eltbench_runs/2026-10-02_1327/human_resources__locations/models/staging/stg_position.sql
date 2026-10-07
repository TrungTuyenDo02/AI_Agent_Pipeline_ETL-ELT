WITH source_data AS (
    SELECT
        CAST(positionID AS BIGINT) AS position_id,
        CAST(positiontitle AS VARCHAR) AS position_title,
        CAST(educationrequired AS VARCHAR) AS education_required,
        CAST(REPLACE(REPLACE(minsalary, 'US$', ''), ',', '') AS DECIMAL(18, 2)) AS min_salary,
        CAST(REPLACE(REPLACE(maxsalary, 'US$', ''), ',', '') AS DECIMAL(18, 2)) AS max_salary
    FROM {{ source('raw', 'position') }}
)
SELECT
    position_id,
    position_title,
    education_required,
    min_salary,
    max_salary
FROM source_data
