WITH sent_campaigns AS (
    SELECT
        id AS campaign_id,
        segment_id,
        send_time
    FROM {{ ref('stg_campaign') }}
    WHERE status = 'sent'
), recipients AS (
    SELECT
        campaign_id,
        member_id,
        list_id
    FROM {{ ref('stg_campaign_recipient') }}
), activity_metrics AS (
    SELECT
        campaign_id,
        member_id,
        CAST(SUM(CASE WHEN action = 'open' THEN 1 ELSE 0 END) AS BIGINT) AS opens,
        CAST(CASE WHEN SUM(CASE WHEN action = 'open' THEN 1 ELSE 0 END) > 0 THEN 1 ELSE 0 END AS BIGINT) AS unique_opens,
        CAST(SUM(CASE WHEN action = 'click' THEN 1 ELSE 0 END) AS BIGINT) AS clicks,
        CAST(CASE WHEN SUM(CASE WHEN action = 'click' THEN 1 ELSE 0 END) > 0 THEN 1 ELSE 0 END AS BIGINT) AS unique_clicks,
        MIN(CASE WHEN action = 'open' THEN timestamp ELSE NULL END) AS first_open_timestamp
    FROM {{ ref('stg_campaign_recipient_activity') }}
    GROUP BY campaign_id, member_id
), unsubscribe_matches AS (
    SELECT DISTINCT
        campaign_id,
        member_id,
        list_id
    FROM {{ ref('stg_unsubscribe') }}
), enriched AS (
    SELECT
        r.campaign_id,
        r.member_id,
        r.list_id,
        c.segment_id,
        c.send_time,
        a.opens,
        a.unique_opens,
        a.clicks,
        a.unique_clicks,
        a.first_open_timestamp,
        u.campaign_id AS unsubscribe_campaign_id
    FROM recipients AS r
    INNER JOIN sent_campaigns AS c
        ON c.campaign_id = r.campaign_id
    LEFT JOIN activity_metrics AS a
        ON a.campaign_id = r.campaign_id
        AND a.member_id = r.member_id
    LEFT JOIN unsubscribe_matches AS u
        ON u.campaign_id = r.campaign_id
        AND u.member_id = r.member_id
        AND u.list_id = r.list_id
)
SELECT
    md5(campaign_id || '-' || member_id) AS email_id,
    campaign_id,
    member_id,
    list_id,
    segment_id,
    COALESCE(opens, 0)::BIGINT AS opens,
    COALESCE(unique_opens, 0)::BIGINT AS unique_opens,
    COALESCE(clicks, 0)::BIGINT AS clicks,
    COALESCE(unique_clicks, 0)::BIGINT AS unique_clicks,
    CASE WHEN COALESCE(unique_opens, 0) > 0 THEN 'True' ELSE 'False' END AS was_opened,
    CASE WHEN COALESCE(unique_clicks, 0) > 0 THEN 'True' ELSE 'False' END AS was_clicked,
    CAST(send_time AS DATE) AS send_timestamp,
    CAST(first_open_timestamp AS DATE) AS first_open_timestamp,
    CASE
        WHEN first_open_timestamp IS NULL THEN NULL
        ELSE (epoch(first_open_timestamp) - epoch(send_time)) / 60.0
    END AS time_to_open_minutes,
    CASE
        WHEN first_open_timestamp IS NULL THEN NULL
        ELSE (epoch(first_open_timestamp) - epoch(send_time)) / 3600.0
    END AS time_to_open_hours,
    CASE
        WHEN first_open_timestamp IS NULL THEN NULL
        ELSE (epoch(first_open_timestamp) - epoch(send_time)) / 86400.0
    END AS time_to_open_days,
    CASE WHEN unsubscribe_campaign_id IS NULL THEN 'False' ELSE 'True' END AS was_unsubscribed
FROM enriched
