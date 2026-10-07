SELECT
    CAST(positionID AS BIGINT) AS positionID,
    CAST(positiontitle AS VARCHAR) AS positiontitle,
    CAST(educationrequired AS VARCHAR) AS educationrequired,
    CAST(NULLIF(regexp_replace(minsalary, '[^0-9.-]', '', 'g'), '') AS DOUBLE) AS minsalary,
    CAST(NULLIF(regexp_replace(maxsalary, '[^0-9.-]', '', 'g'), '') AS DOUBLE) AS maxsalary
FROM {{ source('raw', 'position') }}
