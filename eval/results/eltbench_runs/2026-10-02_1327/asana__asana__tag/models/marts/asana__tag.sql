WITH task_metrics AS (
    SELECT
        task_tag.tag_id,
        COUNT(DISTINCT CASE WHEN task.completed = FALSE THEN task.id END) AS number_of_open_tasks,
        COUNT(DISTINCT CASE
            WHEN task.completed = FALSE AND task.assignee_id IS NOT NULL THEN task.id
        END) AS number_of_assigned_open_tasks,
        COUNT(DISTINCT CASE WHEN task.completed = TRUE THEN task.id END) AS number_of_tasks_completed
    FROM {{ ref('stg_task_tag') }} AS task_tag
    LEFT JOIN {{ ref('stg_task') }} AS task
        ON task_tag.task_id = task.id
    GROUP BY task_tag.tag_id
)
SELECT
    tag.id AS tag_id,
    tag.name AS tag_name,
    tag.created_at AS created_at,
    COALESCE(task_metrics.number_of_open_tasks, 0) AS number_of_open_tasks,
    COALESCE(task_metrics.number_of_assigned_open_tasks, 0) AS number_of_assigned_open_tasks,
    COALESCE(task_metrics.number_of_tasks_completed, 0) AS number_of_tasks_completed
FROM {{ ref('stg_tag') }} AS tag
LEFT JOIN task_metrics
    ON tag.id = task_metrics.tag_id
