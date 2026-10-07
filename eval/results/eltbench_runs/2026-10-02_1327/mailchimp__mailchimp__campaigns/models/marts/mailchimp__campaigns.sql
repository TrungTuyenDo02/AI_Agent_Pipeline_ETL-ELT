WITH campaign AS (
    SELECT
        campaign_id,
        segment_id,
        create_timestamp,
        send_timestamp,
        list_id,
        reply_to_email,
        campaign_type,
        title,
        archive_url,
        authenticate,
        auto_footer,
        auto_tweet,
        clicktale,
        content_type,
        drag_and_drop,
        fb_comments,
        from_name,
        google_analytics,
        inline_css,
        long_archive_url,
        status,
        subject_line,
        template_id,
        timewarp,
        to_name,
        track_ecomm_360,
        track_goals,
        track_html_clicks,
        track_opens,
        track_text_clicks,
        use_conversation
    FROM {{ ref('stg_campaign') }}
), recipient_metrics AS (
    SELECT
        campaign_id,
        COUNT(*)::BIGINT AS sends
    FROM {{ ref('stg_campaign_recipient') }}
    GROUP BY campaign_id
), activity_metrics AS (
    SELECT
        campaign_id,
        SUM(CASE WHEN action = 'open' THEN 1 ELSE 0 END)::BIGINT AS opens,
        SUM(CASE WHEN action = 'click' THEN 1 ELSE 0 END)::BIGINT AS clicks,
        COUNT(DISTINCT CASE WHEN action = 'open' THEN member_id END)::BIGINT AS unique_opens,
        COUNT(DISTINCT CASE WHEN action = 'click' THEN member_id END)::BIGINT AS unique_clicks
    FROM {{ ref('stg_campaign_recipient_activity') }}
    GROUP BY campaign_id
), unsubscribe_metrics AS (
    SELECT
        campaign_id,
        COUNT(*)::BIGINT AS unsubscribes
    FROM {{ ref('stg_unsubscribe') }}
    GROUP BY campaign_id
)
SELECT
    c.campaign_id,
    c.segment_id,
    c.create_timestamp,
    c.send_timestamp,
    c.list_id,
    c.reply_to_email,
    c.campaign_type,
    c.title,
    c.archive_url,
    c.authenticate,
    c.auto_footer,
    c.auto_tweet,
    c.clicktale,
    c.content_type,
    c.drag_and_drop,
    c.fb_comments,
    c.from_name,
    c.google_analytics,
    c.inline_css,
    c.long_archive_url,
    c.status,
    c.subject_line,
    c.template_id,
    c.timewarp,
    c.to_name,
    c.track_ecomm_360,
    c.track_goals,
    c.track_html_clicks,
    c.track_opens,
    c.track_text_clicks,
    c.use_conversation,
    COALESCE(r.sends, 0)::BIGINT AS sends,
    COALESCE(a.opens, 0)::BIGINT AS opens,
    COALESCE(a.clicks, 0)::BIGINT AS clicks,
    COALESCE(a.unique_opens, 0)::BIGINT AS unique_opens,
    COALESCE(a.unique_clicks, 0)::BIGINT AS unique_clicks,
    COALESCE(u.unsubscribes, 0)::BIGINT AS unsubscribes
FROM campaign AS c
LEFT JOIN recipient_metrics AS r
    ON c.campaign_id = r.campaign_id
LEFT JOIN activity_metrics AS a
    ON c.campaign_id = a.campaign_id
LEFT JOIN unsubscribe_metrics AS u
    ON c.campaign_id = u.campaign_id
