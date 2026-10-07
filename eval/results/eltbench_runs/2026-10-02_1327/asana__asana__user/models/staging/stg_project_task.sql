SELECT
    CAST(project_id AS BIGINT) AS project_id,
    CAST(task_id AS BIGINT) AS task_id,
    CAST(_fivetran_synced AS TIMESTAMP) AS _fivetran_synced
FROM {{ source('raw', 'project_task') }}
