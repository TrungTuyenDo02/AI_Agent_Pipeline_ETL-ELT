SELECT
    CAST(student_id AS VARCHAR) AS student_id,
    CAST(capability AS VARCHAR) AS capability,
    CAST(prof_id AS BIGINT) AS prof_id,
    CAST(salary AS VARCHAR) AS salary
FROM {{ source('raw', 'RA') }}
