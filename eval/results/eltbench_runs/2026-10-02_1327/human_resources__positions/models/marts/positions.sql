WITH employee_metrics AS (
    SELECT
        positionID AS position_id,
        CAST(COUNT(*) FILTER (WHERE performance = 'Poor') AS BIGINT) AS num_poor_performing_employees,
        CAST(COUNT(*) FILTER (WHERE gender = 'F') AS BIGINT) AS num_female_employees,
        CAST(100.0 * COUNT(*) FILTER (WHERE salary > 20000) / NULLIF(COUNT(*), 0) AS DOUBLE) AS per_salary_over_20000,
        CAST(AVG(salary) AS DOUBLE) AS avg_salary
    FROM {{ ref('stg_employee') }}
    GROUP BY positionID
), positions_base AS (
    SELECT
        positionID AS position_id,
        positiontitle AS position_title,
        educationrequired AS education_required,
        maxsalary
    FROM {{ ref('stg_position') }}
)
SELECT
    CAST(p.position_id AS BIGINT) AS position_id,
    CAST(p.position_title AS VARCHAR) AS position_title,
    CAST(p.education_required AS VARCHAR) AS education_required,
    CAST(COALESCE(e.num_poor_performing_employees, 0) AS BIGINT) AS num_poor_performing_employees,
    CAST(COALESCE(e.num_female_employees, 0) AS BIGINT) AS num_female_employees,
    CAST(e.per_salary_over_20000 AS DOUBLE) AS per_salary_over_20000,
    CAST(e.avg_salary AS DOUBLE) AS avg_salary,
    CAST(CASE WHEN p.maxsalary <= 70000 THEN 1 ELSE 0 END AS BIGINT) AS has_maximum_salary_no_more_than_70000
FROM positions_base AS p
LEFT JOIN employee_metrics AS e
    ON p.position_id = e.position_id
