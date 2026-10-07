WITH list_base AS (
    SELECT
        list_id,
        date_created,
        name,
        list_rating,
        beamer_address,
        contact_address_1,
        contact_city,
        contact_company,
        contact_country,
        contact_state,
        contact_zip,
        default_from_email,
        default_from_name,
        default_language,
        email_type_option,
        permission_reminder,
        subscribe_url_long,
        subscribe_url_short,
        use_archive_bar,
        visibility
    FROM {{ ref('stg_list') }}
), member_metrics AS (
    SELECT
        list_id,
        COUNT(*)::BIGINT AS count_members,
        MAX(timestamp_signup)::DATE AS most_recent_signup_timestamp
    FROM {{ ref('stg_member') }}
    GROUP BY list_id
), campaign_send_metrics AS (
    SELECT
        recipient.list_id,
        COUNT(*)::BIGINT AS campaign_sends
    FROM {{ ref('stg_campaign_recipient') }} AS recipient
    INNER JOIN {{ ref('stg_campaign') }} AS campaign
        ON recipient.campaign_id = campaign.campaign_id
    WHERE lower(campaign.status) = 'sent'
    GROUP BY recipient.list_id
), campaign_activity_metrics AS (
    SELECT
        activity.list_id,
        COUNT(CASE WHEN activity.action = 'open' THEN 1 END)::BIGINT AS campaign_opens,
        COUNT(CASE WHEN activity.action = 'click' THEN 1 END)::BIGINT AS campaign_clicks,
        COUNT(DISTINCT CASE WHEN activity.action = 'open' THEN activity.campaign_id || '|' || activity.member_id END)::BIGINT AS campaign_unique_opens,
        COUNT(DISTINCT CASE WHEN activity.action = 'click' THEN activity.campaign_id || '|' || activity.member_id END)::BIGINT AS campaign_unique_clicks
    FROM {{ ref('stg_campaign_recipient_activity') }} AS activity
    INNER JOIN {{ ref('stg_campaign') }} AS campaign
        ON activity.campaign_id = campaign.campaign_id
    WHERE lower(campaign.status) = 'sent'
    GROUP BY activity.list_id
), campaign_unsubscribe_metrics AS (
    SELECT
        unsubscribe.list_id,
        COUNT(*)::BIGINT AS campaign_unsubscribes
    FROM {{ ref('stg_unsubscribe') }} AS unsubscribe
    INNER JOIN {{ ref('stg_campaign') }} AS campaign
        ON unsubscribe.campaign_id = campaign.campaign_id
    WHERE lower(campaign.status) = 'sent'
    GROUP BY unsubscribe.list_id
), automation_send_metrics AS (
    SELECT
        list_id,
        COUNT(*)::BIGINT AS automation_sends
    FROM {{ ref('stg_automation_recipient') }}
    GROUP BY list_id
), automation_activity_metrics AS (
    SELECT
        list_id,
        COUNT(CASE WHEN action = 'open' THEN 1 END)::BIGINT AS automation_opens,
        COUNT(CASE WHEN action = 'click' THEN 1 END)::BIGINT AS automation_clicks,
        COUNT(DISTINCT CASE WHEN action = 'open' THEN automation_email_id || '|' || member_id END)::BIGINT AS automation_unique_opens,
        COUNT(DISTINCT CASE WHEN action = 'click' THEN automation_email_id || '|' || member_id END)::BIGINT AS automation_unique_clicks,
        COUNT(CASE WHEN action = 'unsubscribe' THEN 1 END)::BIGINT AS automation_unsubscribes
    FROM {{ ref('stg_automation_recipient_activity') }}
    GROUP BY list_id
)
SELECT
    base.list_id AS list_id,
    base.date_created AS date_created,
    base.name AS name,
    base.list_rating AS list_rating,
    base.beamer_address AS beamer_address,
    base.contact_address_1 AS contact_address_1,
    base.contact_city AS contact_city,
    base.contact_company AS contact_company,
    base.contact_country AS contact_country,
    base.contact_state AS contact_state,
    base.contact_zip AS contact_zip,
    base.default_from_email AS default_from_email,
    base.default_from_name AS default_from_name,
    base.default_language AS default_language,
    base.email_type_option AS email_type_option,
    base.permission_reminder AS permission_reminder,
    base.subscribe_url_long AS subscribe_url_long,
    base.subscribe_url_short AS subscribe_url_short,
    base.use_archive_bar AS use_archive_bar,
    base.visibility AS visibility,
    COALESCE(members.count_members, 0)::BIGINT AS count_members,
    members.most_recent_signup_timestamp AS most_recent_signup_timestamp,
    COALESCE(campaign_sends.campaign_sends, 0)::BIGINT AS campaign_sends,
    COALESCE(campaign_activity.campaign_opens, 0)::BIGINT AS campaign_opens,
    COALESCE(campaign_activity.campaign_clicks, 0)::BIGINT AS campaign_clicks,
    COALESCE(campaign_activity.campaign_unique_opens, 0)::BIGINT AS campaign_unique_opens,
    COALESCE(campaign_activity.campaign_unique_clicks, 0)::BIGINT AS campaign_unique_clicks,
    COALESCE(campaign_unsubscribes.campaign_unsubscribes, 0)::BIGINT AS campaign_unsubscribes,
    COALESCE(automation_sends.automation_sends, 0)::BIGINT AS automation_sends,
    COALESCE(automation_activity.automation_opens, 0)::BIGINT AS automation_opens,
    COALESCE(automation_activity.automation_clicks, 0)::BIGINT AS automation_clicks,
    COALESCE(automation_activity.automation_unique_opens, 0)::BIGINT AS automation_unique_opens,
    COALESCE(automation_activity.automation_unique_clicks, 0)::BIGINT AS automation_unique_clicks,
    COALESCE(automation_activity.automation_unsubscribes, 0)::BIGINT AS automation_unsubscribes
FROM list_base AS base
LEFT JOIN member_metrics AS members
    ON base.list_id = members.list_id
LEFT JOIN campaign_send_metrics AS campaign_sends
    ON base.list_id = campaign_sends.list_id
LEFT JOIN campaign_activity_metrics AS campaign_activity
    ON base.list_id = campaign_activity.list_id
LEFT JOIN campaign_unsubscribe_metrics AS campaign_unsubscribes
    ON base.list_id = campaign_unsubscribes.list_id
LEFT JOIN automation_send_metrics AS automation_sends
    ON base.list_id = automation_sends.list_id
LEFT JOIN automation_activity_metrics AS automation_activity
    ON base.list_id = automation_activity.list_id
