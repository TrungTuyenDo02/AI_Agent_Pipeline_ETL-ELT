SELECT
    CAST(task_id AS BIGINT) AS task_id,
    CAST(user_id AS BIGINT) AS user_id
FROM {{ source('raw', 'task_follower') }}
