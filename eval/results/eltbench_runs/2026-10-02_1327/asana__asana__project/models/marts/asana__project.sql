WITH active_projects AS (
    SELECT
        id AS project_id,
        name AS project_name,
        team_id,
        archived AS is_archived,
        created_at,
        current_status,
        due_date,
        modified_at AS last_modified_at,
        owner_id AS owner_user_id,
        notes
    FROM {{ ref('stg_project') }}
    WHERE _fivetran_deleted = FALSE
),
active_teams AS (
    SELECT
        id AS team_id,
        name AS team_name
    FROM {{ ref('stg_team') }}
    WHERE _fivetran_deleted = FALSE
),
task_metrics AS (
    SELECT
        pt.project_id,
        COUNT(DISTINCT CASE WHEN t.completed = FALSE THEN pt.task_id END) AS number_of_open_tasks,
        COUNT(DISTINCT CASE
            WHEN t.completed = FALSE AND t.assignee_id IS NOT NULL THEN pt.task_id
        END) AS number_of_assigned_open_tasks,
        COUNT(DISTINCT CASE WHEN t.completed = TRUE THEN pt.task_id END) AS number_of_tasks_completed,
        COUNT(DISTINCT t.assignee_id) AS number_of_users_involved
    FROM {{ ref('stg_project_task') }} AS pt
    LEFT JOIN {{ ref('stg_task') }} AS t
        ON pt.task_id = t.id
    GROUP BY pt.project_id
)
SELECT
    p.project_id,
    p.project_name,
    COALESCE(m.number_of_open_tasks, 0) AS number_of_open_tasks,
    COALESCE(m.number_of_assigned_open_tasks, 0) AS number_of_assigned_open_tasks,
    COALESCE(m.number_of_tasks_completed, 0) AS number_of_tasks_completed,
    p.team_id,
    tm.team_name,
    p.is_archived,
    p.created_at,
    p.current_status,
    p.due_date,
    p.last_modified_at,
    p.owner_user_id,
    COALESCE(m.number_of_users_involved, 0) AS number_of_users_involved,
    p.notes
FROM active_projects AS p
LEFT JOIN active_teams AS tm
    ON p.team_id = tm.team_id
LEFT JOIN task_metrics AS m
    ON p.project_id = m.project_id
