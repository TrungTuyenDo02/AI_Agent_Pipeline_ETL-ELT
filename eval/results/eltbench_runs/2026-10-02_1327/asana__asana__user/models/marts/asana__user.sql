WITH users AS (
    SELECT
        id AS user_id,
        email,
        name AS user_name
    FROM {{ ref('stg_user') }}
    WHERE _fivetran_deleted IS DISTINCT FROM TRUE
),
open_task_counts AS (
    SELECT
        assignee_id AS user_id,
        COUNT(DISTINCT id)::BIGINT AS number_of_open_tasks
    FROM {{ ref('stg_task') }}
    WHERE completed = FALSE
    GROUP BY assignee_id
),
completed_task_counts AS (
    SELECT
        CAST(completed_by_id AS BIGINT) AS user_id,
        COUNT(DISTINCT id)::BIGINT AS number_of_tasks_completed
    FROM {{ ref('stg_task') }}
    WHERE completed = TRUE
      AND completed_by_id IS NOT NULL
    GROUP BY CAST(completed_by_id AS BIGINT)
),
owned_project_counts AS (
    SELECT
        owner_id AS user_id,
        COUNT(DISTINCT id)::BIGINT AS number_of_projects_owned
    FROM {{ ref('stg_project') }}
    WHERE _fivetran_deleted IS DISTINCT FROM TRUE
      AND archived = FALSE
    GROUP BY owner_id
),
assigned_project_counts AS (
    SELECT
        t.assignee_id AS user_id,
        COUNT(DISTINCT p.id)::BIGINT AS number_of_projects_currently_assigned_to
    FROM {{ ref('stg_project_task') }} AS pt
    INNER JOIN {{ ref('stg_task') }} AS t
        ON t.id = pt.task_id
    INNER JOIN {{ ref('stg_project') }} AS p
        ON p.id = pt.project_id
    WHERE t.completed = FALSE
      AND p._fivetran_deleted IS DISTINCT FROM TRUE
      AND p.archived = FALSE
    GROUP BY t.assignee_id
)
SELECT
    u.user_id,
    u.email,
    u.user_name,
    COALESCE(ot.number_of_open_tasks, 0)::BIGINT AS number_of_open_tasks,
    COALESCE(ct.number_of_tasks_completed, 0)::BIGINT AS number_of_tasks_completed,
    COALESCE(op.number_of_projects_owned, 0)::BIGINT AS number_of_projects_owned,
    COALESCE(ap.number_of_projects_currently_assigned_to, 0)::BIGINT AS number_of_projects_currently_assigned_to
FROM users AS u
LEFT JOIN open_task_counts AS ot
    ON ot.user_id = u.user_id
LEFT JOIN completed_task_counts AS ct
    ON ct.user_id = u.user_id
LEFT JOIN owned_project_counts AS op
    ON op.user_id = u.user_id
LEFT JOIN assigned_project_counts AS ap
    ON ap.user_id = u.user_id
