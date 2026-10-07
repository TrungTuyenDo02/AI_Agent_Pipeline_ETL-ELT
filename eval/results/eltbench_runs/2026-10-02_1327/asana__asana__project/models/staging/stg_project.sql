SELECT
    CAST(id AS BIGINT) AS id,
    CAST(_fivetran_deleted AS BOOLEAN) AS _fivetran_deleted,
    CAST(archived AS VARCHAR) AS archived,
    CAST(created_at AS VARCHAR) AS created_at,
    CAST(current_status AS VARCHAR) AS current_status,
    CAST(due_date AS DATE) AS due_date,
    CAST(modified_at AS VARCHAR) AS modified_at,
    CAST(name AS VARCHAR) AS name,
    CAST(notes AS VARCHAR) AS notes,
    CAST(owner_id AS BIGINT) AS owner_id,
    CAST(team_id AS BIGINT) AS team_id
FROM {{ source('raw', 'project') }}
