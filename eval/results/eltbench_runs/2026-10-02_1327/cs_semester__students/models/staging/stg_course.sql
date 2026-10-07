SELECT
    CAST(course_id AS BIGINT) AS course_id,
    CAST(name AS VARCHAR) AS name,
    CAST(credit AS BIGINT) AS credit,
    CAST(diff AS BIGINT) AS diff
FROM {{ source('raw', 'course') }}
