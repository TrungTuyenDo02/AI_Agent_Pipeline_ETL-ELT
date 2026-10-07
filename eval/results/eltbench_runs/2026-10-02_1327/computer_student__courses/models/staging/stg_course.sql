SELECT
    CAST(course_id AS BIGINT) AS course_id,
    CAST(courseLevel AS VARCHAR) AS courselevel
FROM {{ source('raw', 'course') }}
