WITH teams AS (
    SELECT
        id AS team_id,
        name AS team_name
    FROM {{ ref('stg_team') }}
    WHERE _fivetran_deleted = FALSE
),
projects AS (
    SELECT DISTINCT
        id AS project_id,
        team_id,
        name AS project_name,
        archived
    FROM {{ ref('stg_project') }}
    WHERE _fivetran_deleted = FALSE
),
project_links AS (
    SELECT DISTINCT
        project_id,
        task_id
    FROM {{ ref('stg_project_task') }}
),
tasks_by_team AS (
    SELECT DISTINCT
        p.team_id,
        t.id AS task_id,
        t.completed,
        t.assignee_id
    FROM projects p
    INNER JOIN project_links pl
        ON pl.project_id = p.project_id
    INNER JOIN {{ ref('stg_task') }} t
        ON t.id = pl.task_id
),
project_metrics AS (
    SELECT
        team_id,
        COUNT(DISTINCT CASE WHEN archived = FALSE THEN project_id END) AS number_of_active_projects,
        string_agg(DISTINCT CASE WHEN archived = FALSE THEN project_name END, ', ' ORDER BY CASE WHEN archived = FALSE THEN project_name END) AS active_projects,
        COUNT(DISTINCT CASE WHEN archived = TRUE THEN project_id END) AS number_of_archived_projects
    FROM projects
    GROUP BY team_id
),
task_metrics AS (
    SELECT
        team_id,
        COUNT(DISTINCT CASE WHEN completed = FALSE THEN task_id END) AS number_of_open_tasks,
        COUNT(DISTINCT CASE WHEN completed = FALSE AND assignee_id IS NOT NULL THEN task_id END) AS number_of_assigned_open_tasks,
        COUNT(DISTINCT CASE WHEN completed = TRUE THEN task_id END) AS number_of_tasks_completed
    FROM tasks_by_team
    GROUP BY team_id
)
SELECT
    t.team_id,
    t.team_name,
    COALESCE(tm.number_of_open_tasks, 0)::BIGINT AS number_of_open_tasks,
    COALESCE(tm.number_of_assigned_open_tasks, 0)::BIGINT AS number_of_assigned_open_tasks,
    COALESCE(tm.number_of_tasks_completed, 0)::BIGINT AS number_of_tasks_completed,
    COALESCE(pm.number_of_active_projects, 0)::BIGINT AS number_of_active_projects,
    pm.active_projects::VARCHAR AS active_projects,
    COALESCE(pm.number_of_archived_projects, 0)::BIGINT AS number_of_archived_projects
FROM teams t
LEFT JOIN task_metrics tm
    ON tm.team_id = t.team_id
LEFT JOIN project_metrics pm
    ON pm.team_id = t.team_id
