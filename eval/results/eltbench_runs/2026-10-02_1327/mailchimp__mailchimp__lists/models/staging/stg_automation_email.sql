SELECT
    CAST(id AS VARCHAR) AS automation_email_id,
    CAST(automation_id AS VARCHAR) AS automation_id
FROM {{ source('raw', 'automation_email') }}
WHERE _fivetran_deleted = FALSE
