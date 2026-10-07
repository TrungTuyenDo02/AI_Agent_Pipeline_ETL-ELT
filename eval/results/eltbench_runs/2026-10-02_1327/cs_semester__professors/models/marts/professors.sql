WITH ra_enriched AS (
    SELECT
        r.student_id,
        r.prof_id,
        r.capability,
        r.salary,
        s.type AS student_type
    FROM {{ ref('stg_RA') }} AS r
    LEFT JOIN {{ ref('stg_student') }} AS s
        ON r.student_id = s.student_id
),
ra_ranked AS (
    SELECT
        student_id,
        prof_id,
        capability,
        salary,
        student_type,
        MAX(capability) OVER (PARTITION BY prof_id) AS max_capability
    FROM ra_enriched
),
ra_metrics AS (
    SELECT
        prof_id,
        COUNT(student_id) AS num_ra,
        SUM(CASE WHEN student_type = 'TPG' THEN 1 ELSE 0 END) AS num_tpg,
        SUM(CASE WHEN capability = max_capability THEN 1 ELSE 0 END) AS num_highest_research_ability,
        SUM(CASE WHEN salary = 'high' THEN 1 ELSE 0 END) AS num_high_salary
    FROM ra_ranked
    GROUP BY prof_id
),
average_teaching AS (
    SELECT AVG(teachingability) AS avg_teachingability
    FROM {{ ref('stg_prof') }}
)
SELECT
    CAST(p.prof_id AS BIGINT) AS prof_id,
    CAST(p.first_name AS VARCHAR) AS first_name,
    CAST(p.last_name AS VARCHAR) AS last_name,
    CAST(COALESCE(m.num_ra, 0) AS BIGINT) AS "num_RA",
    CAST(
        CASE
            WHEN COALESCE(m.num_ra, 0) = 0 THEN 0.0
            ELSE 100.0 * COALESCE(m.num_tpg, 0) / m.num_ra
        END AS DOUBLE
    ) AS percentage_of_RA_tpg,
    CAST(COALESCE(m.num_highest_research_ability, 0) AS BIGINT) AS num_students_with_the_highest_research_ability,
    CAST(
        CASE
            WHEN p.teachingability > a.avg_teachingability
                AND COALESCE(m.num_ra, 0) > 1
            THEN 1
            ELSE 0
        END AS BIGINT
    ) AS has_more_than_average_teaching_ability_and_1_student,
    CAST(COALESCE(m.num_high_salary, 0) AS BIGINT) AS num_of_students_high_salary
FROM {{ ref('stg_prof') }} AS p
CROSS JOIN average_teaching AS a
LEFT JOIN ra_metrics AS m
    ON p.prof_id = m.prof_id
