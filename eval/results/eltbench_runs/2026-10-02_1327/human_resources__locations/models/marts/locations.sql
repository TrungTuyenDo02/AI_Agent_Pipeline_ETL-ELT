WITH employee_enriched AS (
    SELECT
        e.location_id,
        e.firstname,
        e.lastname,
        e.ssn,
        e.salary_amount,
        p.position_title,
        e.performance
    FROM {{ ref('stg_employee') }} AS e
    LEFT JOIN {{ ref('stg_position') }} AS p
        ON e.position_id = p.position_id
),
ranked_employees AS (
    SELECT
        location_id,
        firstname,
        lastname,
        salary_amount,
        position_title,
        performance,
        ROW_NUMBER() OVER (
            PARTITION BY location_id
            ORDER BY salary_amount DESC NULLS LAST, lastname ASC, firstname ASC, ssn ASC
        ) AS employee_rank
    FROM employee_enriched
),
employee_metrics AS (
    SELECT
        location_id,
        COUNT(*)::BIGINT AS num_employees,
        MAX(CASE WHEN employee_rank = 1 THEN firstname || ' ' || lastname END) AS highest_paid_employee,
        COUNT(CASE WHEN position_title = 'Trainee' THEN 1 END)::BIGINT AS num_of_trainee,
        COUNT(CASE WHEN position_title = 'Account Representative' AND performance = 'Average' THEN 1 END)::BIGINT AS num_account_representatives_with_average_performance,
        COUNT(CASE WHEN performance = 'Good' THEN 1 END)::BIGINT AS num_employees_have_good_performance
    FROM ranked_employees
    GROUP BY location_id
)
SELECT
    l.location_id,
    l.state AS location_state,
    l.address AS location_address,
    COALESCE(m.num_employees, 0)::BIGINT AS num_employees,
    m.highest_paid_employee,
    COALESCE(m.num_of_trainee, 0)::BIGINT AS num_of_trainee,
    COALESCE(m.num_account_representatives_with_average_performance, 0)::BIGINT AS "num_Account_Representatives_with_Average_performance",
    COALESCE(m.num_employees_have_good_performance, 0)::BIGINT AS num_employees_have_good_perfomance
FROM {{ ref('stg_location') }} AS l
LEFT JOIN employee_metrics AS m
    ON l.location_id = m.location_id
