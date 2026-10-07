{{ config(materialized='view') }}

SELECT
    CAST(action AS VARCHAR) AS action,
    CAST(automation_email_id AS VARCHAR) AS automation_email_id,
    CAST(member_id AS VARCHAR) AS member_id,
    CAST(timestamp AS VARCHAR) AS activity_timestamp,
    CAST(ip AS VARCHAR) AS ip_address,
    CAST(list_id AS VARCHAR) AS list_id,
    CAST(url AS VARCHAR) AS url
FROM {{ source('raw', 'automation_recipient_activity') }}
