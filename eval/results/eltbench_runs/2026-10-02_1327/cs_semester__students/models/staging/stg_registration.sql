SELECT
    CAST(course_id AS BIGINT) AS course_id,
    CAST(student_id AS BIGINT) AS student_id,
    CAST(grade AS VARCHAR) AS grade,
    CAST(sat AS BIGINT) AS sat
FROM {{ source('raw', 'registration') }}
