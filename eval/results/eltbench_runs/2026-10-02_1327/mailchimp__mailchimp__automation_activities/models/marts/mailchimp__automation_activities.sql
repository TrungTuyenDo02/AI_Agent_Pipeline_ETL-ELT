{{ config(materialized='table') }}

WITH activities AS (
    SELECT
        action,
        automation_email_id,
        member_id,
        activity_timestamp,
        ip_address,
        list_id,
        url
    FROM {{ ref('stg_automation_recipient_activity') }}
    WHERE action IN ('open', 'click', 'bounce')
),
automation_emails AS (
    SELECT
        id,
        automation_id
    FROM {{ ref('stg_automation_email') }}
),
automations AS (
    SELECT
        id,
        segment_id
    FROM {{ ref('stg_automation') }}
),
joined AS (
    SELECT
        activities.action AS action_type,
        activities.automation_email_id AS automation_email_id,
        activities.member_id AS member_id,
        activities.list_id AS list_id,
        activities.activity_timestamp AS activity_timestamp,
        activities.ip_address AS ip_address,
        COALESCE(activities.url, '') AS url,
        CAST(NULL AS VARCHAR) AS activity_id,
        automation_emails.automation_id AS automation_id,
        COALESCE(automations.segment_id, '') AS segment_id
    FROM activities
    LEFT JOIN automation_emails
        ON activities.automation_email_id = automation_emails.id
    LEFT JOIN automations
        ON automation_emails.automation_id = automations.id
)
SELECT
    action_type,
    automation_email_id,
    member_id,
    list_id,
    activity_timestamp,
    ip_address,
    url,
    activity_id,
    automation_id,
    segment_id
FROM joined
