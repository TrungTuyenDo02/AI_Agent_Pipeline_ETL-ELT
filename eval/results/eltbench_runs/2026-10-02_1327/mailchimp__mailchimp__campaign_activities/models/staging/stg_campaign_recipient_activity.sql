WITH source_data AS (
    SELECT
        CAST(action AS VARCHAR) AS action,
        CAST(campaign_id AS VARCHAR) AS campaign_id,
        CAST(member_id AS VARCHAR) AS member_id,
        CAST("timestamp" AS TIMESTAMP) AS activity_timestamp,
        CAST(ip AS VARCHAR) AS ip_address,
        CAST(list_id AS VARCHAR) AS list_id,
        CAST(url AS VARCHAR) AS url
    FROM {{ source('raw', 'campaign_recipient_activity') }}
)
SELECT
    lower(trim(action)) AS action_type,
    campaign_id,
    member_id,
    list_id,
    activity_timestamp,
    ip_address,
    CASE
        WHEN lower(trim(action)) = 'click' THEN url
        ELSE NULL
    END AS url
FROM source_data
WHERE lower(trim(action)) IN ('open', 'click', 'bounce')
