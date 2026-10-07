SELECT
    CAST(id AS BIGINT) AS id,
    CAST(assignee_id AS BIGINT) AS assignee_id,
    CASE WHEN completed THEN 1 ELSE 0 END AS completed,
    CAST(completed_at AS VARCHAR) AS completed_at,
    CAST(created_at AS VARCHAR) AS created_at,
    CAST(due_on AS DATE) AS due_on,
    CAST(modified_at AS VARCHAR) AS modified_at,
    CAST(name AS VARCHAR) AS name,
    CAST(parent_id AS VARCHAR) AS parent_id,
    CAST(workspace_id AS BIGINT) AS workspace_id
FROM {{ source('raw', 'task') }}
