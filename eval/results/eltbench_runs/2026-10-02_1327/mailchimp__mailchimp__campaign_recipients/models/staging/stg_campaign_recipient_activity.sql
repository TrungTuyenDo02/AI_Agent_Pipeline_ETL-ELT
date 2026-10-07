SELECT
    CAST(action AS VARCHAR) AS action,
    CAST(campaign_id AS VARCHAR) AS campaign_id,
    CAST(member_id AS VARCHAR) AS member_id,
    CAST(timestamp AS TIMESTAMP) AS timestamp
FROM {{ source('raw', 'campaign_recipient_activity') }}
