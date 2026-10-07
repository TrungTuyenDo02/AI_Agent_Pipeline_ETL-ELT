SELECT
    CAST(id AS BIGINT) AS id,
    CAST(assignee_id AS BIGINT) AS assignee_id,
    CAST(completed AS BOOLEAN) AS completed
FROM {{ source('raw', 'task') }}
