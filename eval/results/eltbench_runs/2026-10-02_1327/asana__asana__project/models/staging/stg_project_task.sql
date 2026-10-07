SELECT
    CAST(project_id AS BIGINT) AS project_id,
    CAST(task_id AS BIGINT) AS task_id
FROM {{ source('raw', 'project_task') }}
