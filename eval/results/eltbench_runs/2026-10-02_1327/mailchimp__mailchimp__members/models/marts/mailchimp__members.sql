with campaign_metrics as (
    select
        member_id,
        list_id,
        count(*)::bigint as campaign_sends
    from {{ ref('stg_campaign_recipient') }}
    group by member_id, list_id
), campaign_activity_metrics as (
    select
        member_id,
        list_id,
        count(*) filter (where action = 'open')::bigint as campaign_opens,
        count(*) filter (where action = 'click')::bigint as campaign_clicks,
        count(distinct campaign_id) filter (where action = 'open')::bigint as campaign_unique_opens,
        count(distinct campaign_id) filter (where action = 'click')::bigint as campaign_unique_clicks,
        count(*) filter (where action = 'unsubscribe')::bigint as campaign_unsubscribes
    from {{ ref('stg_campaign_recipient_activity') }}
    group by member_id, list_id
), automation_metrics as (
    select
        member_id,
        list_id,
        count(*)::bigint as automation_sends
    from {{ ref('stg_automation_recipient') }}
    group by member_id, list_id
), automation_activity_metrics as (
    select
        member_id,
        list_id,
        count(*) filter (where action = 'open')::bigint as automation_opens,
        count(*) filter (where action = 'click')::bigint as automation_clicks,
        count(distinct automation_email_id) filter (where action = 'open')::bigint as automation_unique_opens,
        count(distinct automation_email_id) filter (where action = 'click')::bigint as automation_unique_clicks,
        count(*) filter (where action = 'unsubscribe')::bigint as automation_unsubscribes
    from {{ ref('stg_automation_recipient_activity') }}
    group by member_id, list_id
)
select
    m.member_id,
    m.email_address,
    m.email_client,
    m.email_type,
    m.status,
    m.list_id,
    m.signup_timestamp,
    m.opt_in_timestamp,
    m.last_changed_timestamp,
    m.country_code,
    m.dstoff,
    m.gmtoff,
    m.opt_in_ip_address,
    m.signup_ip_address,
    m.language,
    m.latitude,
    m.longitude,
    m.member_rating,
    m.timezone,
    m.unique_email_id,
    m.vip,
    coalesce(cm.campaign_sends, 0)::bigint as campaign_sends,
    coalesce(cam.campaign_opens, 0)::bigint as campaign_opens,
    coalesce(cam.campaign_clicks, 0)::bigint as campaign_clicks,
    coalesce(cam.campaign_unique_opens, 0)::bigint as campaign_unique_opens,
    coalesce(cam.campaign_unique_clicks, 0)::bigint as campaign_unique_clicks,
    coalesce(cam.campaign_unsubscribes, 0)::bigint as campaign_unsubscribes,
    coalesce(am.automation_sends, 0)::bigint as automation_sends,
    coalesce(aam.automation_opens, 0)::bigint as automation_opens,
    coalesce(aam.automation_clicks, 0)::bigint as automation_clicks,
    coalesce(aam.automation_unique_opens, 0)::bigint as automation_unique_opens,
    coalesce(aam.automation_unique_clicks, 0)::bigint as automation_unique_clicks,
    coalesce(aam.automation_unsubscribes, 0)::bigint as automation_unsubscribes
from {{ ref('stg_member') }} as m
left join campaign_metrics as cm
    on m.member_id = cm.member_id
    and m.list_id = cm.list_id
left join campaign_activity_metrics as cam
    on m.member_id = cam.member_id
    and m.list_id = cam.list_id
left join automation_metrics as am
    on m.member_id = am.member_id
    and m.list_id = am.list_id
left join automation_activity_metrics as aam
    on m.member_id = aam.member_id
    and m.list_id = aam.list_id
