SELECT
    CAST(id AS BIGINT) AS id,
    CAST(assignee_id AS BIGINT) AS assignee_id,
    CAST(completed AS BOOLEAN) AS completed,
    CAST(completed_at AS TIMESTAMP WITH TIME ZONE) AS completed_at,
    CAST(completed_by_id AS VARCHAR) AS completed_by_id,
    CAST(created_at AS TIMESTAMP WITH TIME ZONE) AS created_at,
    CAST(due_on AS TIMESTAMP WITH TIME ZONE) AS due_on,
    CAST(due_at AS VARCHAR) AS due_at,
    CAST(modified_at AS TIMESTAMP WITH TIME ZONE) AS modified_at,
    CAST(name AS VARCHAR) AS name,
    CAST(parent_id AS VARCHAR) AS parent_id,
    CAST(start_on AS VARCHAR) AS start_on,
    CAST(notes AS VARCHAR) AS notes,
    CAST(workspace_id AS BIGINT) AS workspace_id
FROM {{ source('raw', 'task') }}
