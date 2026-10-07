SELECT
    CAST(id AS BIGINT) AS id,
    CAST(_fivetran_deleted AS BOOLEAN) AS _fivetran_deleted,
    CAST(_fivetran_synced AS TIMESTAMP) AS _fivetran_synced,
    CAST(archived AS BOOLEAN) AS archived,
    CAST(color AS VARCHAR) AS color,
    CAST(created_at AS TIMESTAMP) AS created_at,
    CAST(current_status AS VARCHAR) AS current_status,
    CAST(due_date AS TIMESTAMP) AS due_date,
    CAST(modified_at AS TIMESTAMP) AS modified_at,
    CAST(name AS VARCHAR) AS name,
    CAST(notes AS VARCHAR) AS notes,
    CAST(owner_id AS BIGINT) AS owner_id,
    CAST(public AS VARCHAR) AS public,
    CAST(team_id AS BIGINT) AS team_id,
    CAST(workspace_id AS BIGINT) AS workspace_id
FROM {{ source('raw', 'project') }}
