SELECT
    CAST(campaign_id AS VARCHAR) AS campaign_id,
    CAST(member_id AS VARCHAR) AS member_id,
    CAST(list_id AS VARCHAR) AS list_id,
    CAST(timestamp AS TIMESTAMP) AS timestamp
FROM {{ source('raw', 'unsubscribe') }}
