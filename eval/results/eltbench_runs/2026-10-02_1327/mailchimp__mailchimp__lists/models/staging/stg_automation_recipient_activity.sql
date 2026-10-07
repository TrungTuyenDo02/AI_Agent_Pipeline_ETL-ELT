SELECT
    CAST(action AS VARCHAR) AS action,
    CAST(automation_email_id AS VARCHAR) AS automation_email_id,
    CAST(member_id AS VARCHAR) AS member_id,
    CAST(list_id AS VARCHAR) AS list_id
FROM {{ source('raw', 'automation_recipient_activity') }}
