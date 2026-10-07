{{ config(materialized='table') }}

WITH registration_metrics AS (
    SELECT
        r.course_id,
        CAST(COALESCE(SUM(CASE WHEN r.grade = 'A' THEN 1 ELSE 0 END), 0) AS BIGINT) AS num_students_got_A,
        CAST(100.0 * SUM(CASE WHEN r.sat = 5 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0) AS DOUBLE) AS per_of_students_highest_satisfaction_score_for_the_course,
        CAST(COALESCE(SUM(CASE WHEN r.grade = 'F' THEN 1 ELSE 0 END), 0) AS BIGINT) AS number_of_students_fail,
        CAST(100.0 * SUM(CASE WHEN s.type = 'RPG' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0) AS DOUBLE) AS percentage_of_UG,
        CAST(AVG(r.sat) AS DOUBLE) AS average_satisfying_degree
    FROM {{ ref('stg_registration') }} AS r
    LEFT JOIN {{ ref('stg_student') }} AS s
        ON CAST(r.student_id AS VARCHAR) = s.student_id
    GROUP BY r.course_id
)
SELECT
    c.course_id,
    c.name,
    c.credit,
    COALESCE(m.num_students_got_A, 0) AS num_students_got_A,
    m.per_of_students_highest_satisfaction_score_for_the_course,
    COALESCE(m.number_of_students_fail, 0) AS number_of_students_fail,
    m.percentage_of_UG,
    m.average_satisfying_degree
FROM {{ ref('stg_course') }} AS c
LEFT JOIN registration_metrics AS m
    ON c.course_id = m.course_id
