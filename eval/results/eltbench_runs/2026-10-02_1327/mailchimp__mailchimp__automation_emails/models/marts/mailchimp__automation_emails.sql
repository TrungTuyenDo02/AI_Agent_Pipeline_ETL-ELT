WITH recipient_metrics AS (
    SELECT
        automation_email_id,
        COUNT(*)::BIGINT AS sends
    FROM {{ ref('stg_automation_recipient') }}
    GROUP BY automation_email_id
), activity_metrics AS (
    SELECT
        automation_email_id,
        COUNT(*) FILTER (WHERE lower(action) = 'open')::BIGINT AS opens,
        COUNT(*) FILTER (WHERE lower(action) = 'click')::BIGINT AS clicks,
        COUNT(DISTINCT member_id) FILTER (WHERE lower(action) = 'open')::BIGINT AS unique_opens,
        COUNT(DISTINCT member_id) FILTER (WHERE lower(action) = 'click')::BIGINT AS unique_clicks
    FROM {{ ref('stg_automation_recipient_activity') }}
    GROUP BY automation_email_id
), unsubscribe_metrics AS (
    SELECT
        campaign_id AS automation_email_id,
        COUNT(*)::BIGINT AS unsubscribes
    FROM {{ ref('stg_unsubscribe') }}
    GROUP BY campaign_id
)
SELECT
    email.id AS automation_email_id,
    email.automation_id AS automation_id,
    email.create_time AS created_timestamp,
    email.start_time AS started_timestamp,
    email.send_time AS send_timestamp,
    email.from_name AS from_name,
    email.reply_to AS reply_to,
    email.status AS status,
    email.subject_line AS subject_line,
    email.title AS title,
    email.archive_url AS archive_url,
    email.authenticate AS authenticate,
    email.auto_footer AS auto_footer,
    email.auto_tweet AS auto_tweet,
    email.content_type AS content_type,
    email.delay_action AS delay_action,
    email.delay_action_description AS delay_action_description,
    email.delay_amount AS delay_amount,
    email.delay_full_description AS delay_full_description,
    email.delay_type AS delay_type,
    email.drag_and_drop AS drag_and_drop,
    email.fb_comments AS fb_comments,
    email.google_analytics AS google_analytics,
    email.inline_css AS inline_css,
    email.position AS position,
    email.template_id AS template_id,
    email.track_ecomm_360 AS track_ecomm_360,
    email.track_goals AS track_goals,
    email.track_html_clicks AS track_html_clicks,
    email.track_opens AS track_opens,
    email.track_text_clicks AS track_text_clicks,
    automation.list_id AS list_id,
    automation.segment_id AS segment_id,
    COALESCE(recipient_metrics.sends, 0)::BIGINT AS sends,
    COALESCE(activity_metrics.opens, 0)::BIGINT AS opens,
    COALESCE(activity_metrics.clicks, 0)::BIGINT AS clicks,
    COALESCE(activity_metrics.unique_opens, 0)::BIGINT AS unique_opens,
    COALESCE(activity_metrics.unique_clicks, 0)::BIGINT AS unique_clicks,
    COALESCE(unsubscribe_metrics.unsubscribes, 0)::BIGINT AS unsubscribes
FROM {{ ref('stg_automation_email') }} AS email
LEFT JOIN {{ ref('stg_automation') }} AS automation
    ON email.automation_id = automation.id
LEFT JOIN recipient_metrics
    ON email.id = recipient_metrics.automation_email_id
LEFT JOIN activity_metrics
    ON email.id = activity_metrics.automation_email_id
LEFT JOIN unsubscribe_metrics
    ON email.id = unsubscribe_metrics.automation_email_id
