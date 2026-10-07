SELECT
    CAST(tag_id AS BIGINT) AS tag_id,
    CAST(task_id AS BIGINT) AS task_id
FROM {{ source('raw', 'task_tag') }}
