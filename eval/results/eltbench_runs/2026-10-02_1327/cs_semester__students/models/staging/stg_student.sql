SELECT
    CAST(student_id AS VARCHAR) AS student_id,
    CAST(f_name AS VARCHAR) AS f_name,
    CAST(l_name AS VARCHAR) AS l_name,
    CAST(phone_number AS VARCHAR) AS phone_number,
    CAST(email AS VARCHAR) AS email,
    CAST(intelligence AS BIGINT) AS intelligence,
    CAST(gpa AS DOUBLE) AS gpa,
    CAST(type AS VARCHAR) AS type
FROM {{ source('raw', 'student') }}
