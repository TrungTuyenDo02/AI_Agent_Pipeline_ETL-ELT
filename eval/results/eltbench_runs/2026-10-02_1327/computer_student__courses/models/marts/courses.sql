WITH professor_counts AS (
    SELECT
        t.course_id,
        COUNT(DISTINCT CASE WHEN p.professor = 1 THEN t.p_id END)::BIGINT AS number_of_professors,
        COUNT(DISTINCT CASE WHEN p.professor = 1 AND p.hasposition <> 'Faculty' THEN t.p_id END)::BIGINT AS number_of_professors_not_faculty,
        COUNT(DISTINCT CASE WHEN p.professor = 1 AND p.hasposition = 'Faculty' THEN t.p_id END)::BIGINT AS number_of_professors_faculty
    FROM {{ ref('stg_taught_by') }} AS t
    LEFT JOIN {{ ref('stg_person') }} AS p
        ON t.p_id = p.p_id
    GROUP BY t.course_id
), advisor_courses AS (
    SELECT DISTINCT
        t.course_id
    FROM {{ ref('stg_taught_by') }} AS t
    INNER JOIN {{ ref('stg_advisedBy') }} AS a
        ON t.p_id = a.p_id
)
SELECT
    c.course_id AS course_id,
    c.courselevel AS courselevel,
    COALESCE(pc.number_of_professors, 0)::BIGINT AS number_of_professors,
    COALESCE(pc.number_of_professors_not_faculty, 0)::BIGINT AS number_of_professors_not_faculty,
    COALESCE(pc.number_of_professors_faculty, 0)::BIGINT AS number_of_professors_faculty,
    CASE
        WHEN COALESCE(pc.number_of_professors, 0) > 4 THEN 1
        ELSE 0
    END::BIGINT AS taught_by_more_than_4_people,
    CASE
        WHEN ac.course_id IS NOT NULL THEN 1
        ELSE 0
    END::BIGINT AS taught_by_the_advisors
FROM {{ ref('stg_course') }} AS c
LEFT JOIN professor_counts AS pc
    ON c.course_id = pc.course_id
LEFT JOIN advisor_courses AS ac
    ON c.course_id = ac.course_id
