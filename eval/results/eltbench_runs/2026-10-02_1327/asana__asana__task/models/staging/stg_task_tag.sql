SELECT
    CAST(task_id AS BIGINT) AS task_id,
    CAST(tag_id AS BIGINT) AS tag_id
FROM {{ source('raw', 'task_tag') }}
