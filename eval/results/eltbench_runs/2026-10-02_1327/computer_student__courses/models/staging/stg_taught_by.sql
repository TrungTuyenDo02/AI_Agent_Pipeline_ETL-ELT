SELECT
    CAST(course_id AS BIGINT) AS course_id,
    CAST(p_id AS BIGINT) AS p_id
FROM {{ source('raw', 'taught_by') }}
