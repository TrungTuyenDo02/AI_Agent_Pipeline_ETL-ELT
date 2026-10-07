WITH automations AS (
    SELECT
        id AS automation_id,
        list_id,
        segment_id,
        segment_text,
        start_time,
        create_time,
        status,
        title,
        trigger_settings
    FROM {{ ref('stg_automation') }}
    WHERE COALESCE(_fivetran_deleted, FALSE) = FALSE
),
automation_emails AS (
    SELECT
        id,
        automation_id
    FROM {{ ref('stg_automation_email') }}
    WHERE COALESCE(_fivetran_deleted, FALSE) = FALSE
),
sends AS (
    SELECT
        ae.automation_id,
        COUNT(*) AS sends
    FROM automation_emails ae
    INNER JOIN {{ ref('stg_automation_recipient') }} ar
        ON ar.automation_email_id = ae.id
    GROUP BY ae.automation_id
),
activity_metrics AS (
    SELECT
        ae.automation_id,
        COUNT(*) FILTER (WHERE ara.action = 'open') AS opens,
        COUNT(*) FILTER (WHERE ara.action = 'click') AS clicks,
        COUNT(DISTINCT CASE WHEN ara.action = 'open' THEN ara.member_id END) AS unique_opens,
        COUNT(DISTINCT CASE WHEN ara.action = 'click' THEN ara.member_id END) AS unique_clicks
    FROM automation_emails ae
    INNER JOIN {{ ref('stg_automation_recipient_activity') }} ara
        ON ara.automation_email_id = ae.id
    GROUP BY ae.automation_id
),
unsubscribe_metrics AS (
    SELECT
        ae.automation_id,
        COUNT(DISTINCT u.member_id) AS unsubscribes
    FROM automation_emails ae
    INNER JOIN {{ ref('stg_unsubscribe') }} u
        ON u.campaign_id = ae.id
    GROUP BY ae.automation_id
)
SELECT
    a.automation_id,
    a.list_id,
    a.segment_id,
    a.segment_text,
    a.start_time AS started_timestamp,
    a.create_time AS created_timestamp,
    a.status,
    a.title,
    a.trigger_settings,
    COALESCE(s.sends, 0) AS sends,
    COALESCE(am.opens, 0) AS opens,
    COALESCE(am.clicks, 0) AS clicks,
    COALESCE(am.unique_opens, 0) AS unique_opens,
    COALESCE(am.unique_clicks, 0) AS unique_clicks,
    COALESCE(um.unsubscribes, 0) AS unsubscribes
FROM automations a
LEFT JOIN sends s
    ON s.automation_id = a.automation_id
LEFT JOIN activity_metrics am
    ON am.automation_id = a.automation_id
LEFT JOIN unsubscribe_metrics um
    ON um.automation_id = a.automation_id
