SELECT
    CAST(ssn AS VARCHAR) AS ssn,
    CAST(lastname AS VARCHAR) AS lastname,
    CAST(firstname AS VARCHAR) AS firstname,
    CAST(hiredate AS DATE) AS hiredate,
    CAST(NULLIF(regexp_replace(salary, '[^0-9.-]', '', 'g'), '') AS DOUBLE) AS salary,
    CAST(gender AS VARCHAR) AS gender,
    CAST(performance AS VARCHAR) AS performance,
    CAST(positionID AS BIGINT) AS positionID,
    CAST(locationID AS BIGINT) AS locationID
FROM {{ source('raw', 'employee') }}
