WITH registration_metrics AS (
    SELECT
        r.student_id,
        AVG(
            CASE r.grade
                WHEN 'A' THEN 4.0
                WHEN 'B' THEN 3.0
                WHEN 'C' THEN 2.0
                WHEN 'D' THEN 1.0
                WHEN 'F' THEN 0.0
                ELSE NULL
            END
        ) AS GPA_based_on_registration,
        COUNT(DISTINCT r.course_id) AS num_courses_taken
    FROM {{ ref('stg_registration') }} AS r
    GROUP BY r.student_id
),
mlt_b_students AS (
    SELECT DISTINCT
        r.student_id
    FROM {{ ref('stg_registration') }} AS r
    INNER JOIN {{ ref('stg_course') }} AS c
        ON r.course_id = c.course_id
    WHERE c.name = 'Machine Learning Theory'
      AND r.grade = 'B'
),
highest_tpg_intelligence AS (
    SELECT MAX(s.intelligence) AS max_intelligence
    FROM {{ ref('stg_student') }} AS s
    WHERE s.type = 'TPG'
),
most_popular_professor AS (
    SELECT MAX(p.popularity) AS max_popularity
    FROM {{ ref('stg_prof') }} AS p
),
supervised_by_most_popular AS (
    SELECT DISTINCT
        ra.student_id
    FROM {{ ref('stg_RA') }} AS ra
    INNER JOIN {{ ref('stg_prof') }} AS p
        ON ra.prof_id = p.prof_id
    CROSS JOIN most_popular_professor AS mpp
    WHERE p.popularity = mpp.max_popularity
)
SELECT
    s.student_id AS student_id,
    s.f_name AS first_name,
    s.l_name AS last_name,
    CASE
        WHEN mlt.student_id IS NOT NULL AND s.gpa > 3.0 THEN 1
        ELSE 0
    END AS got_B_in_MLT_and_gpa_over3,
    CASE
        WHEN s.type = 'TPG'
         AND s.intelligence = hti.max_intelligence THEN 1
        ELSE 0
    END AS has_the_highest_intelligence_UG,
    CASE
        WHEN smp.student_id IS NOT NULL THEN 1
        ELSE 0
    END AS is_under_supervision_of_most_popular_professor,
    rm.GPA_based_on_registration AS GPA_based_on_registration,
    COALESCE(rm.num_courses_taken, 0) AS num_courses_taken
FROM {{ ref('stg_student') }} AS s
CROSS JOIN highest_tpg_intelligence AS hti
LEFT JOIN registration_metrics AS rm
    ON CAST(s.student_id AS BIGINT) = rm.student_id
LEFT JOIN mlt_b_students AS mlt
    ON CAST(s.student_id AS BIGINT) = mlt.student_id
LEFT JOIN supervised_by_most_popular AS smp
    ON s.student_id = smp.student_id
