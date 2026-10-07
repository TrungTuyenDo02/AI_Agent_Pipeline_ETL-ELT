SELECT
    CAST(prof_id AS BIGINT) AS prof_id,
    CAST(gender AS VARCHAR) AS gender,
    CAST(first_name AS VARCHAR) AS first_name,
    CAST(last_name AS VARCHAR) AS last_name,
    CAST(email AS VARCHAR) AS email,
    CAST(popularity AS BIGINT) AS popularity,
    CAST(teachingability AS BIGINT) AS teachingability,
    CAST(graduate_from AS VARCHAR) AS graduate_from
FROM {{ source('raw', 'prof') }}
