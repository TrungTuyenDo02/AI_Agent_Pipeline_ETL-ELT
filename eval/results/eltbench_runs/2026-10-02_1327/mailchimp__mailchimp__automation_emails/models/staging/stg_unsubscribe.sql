SELECT
    CAST(campaign_id AS VARCHAR) AS campaign_id,
    CAST(member_id AS VARCHAR) AS member_id
FROM {{ source('raw', 'unsubscribe') }}
