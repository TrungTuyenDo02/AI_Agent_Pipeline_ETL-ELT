{{ config(materialized='table') }}

with segments as (
    select
        id as segment_id,
        list_id,
        member_count,
        name as segment_name,
        type as segment_type,
        updated_at as updated_timestamp,
        created_at as created_timestamp
    from {{ ref('stg_segment') }}
),
segment_members as (
    select distinct
        segment_id,
        list_id,
        member_id
    from {{ ref('stg_segment_member') }}
),
sent_campaigns as (
    select distinct id as campaign_id, list_id
    from {{ ref('stg_campaign') }}
    where status = 'sent'
),
campaign_sends as (
    select
        sm.segment_id,
        sm.list_id,
        count(*)::BIGINT as campaign_sends
    from sent_campaigns sc
    inner join {{ ref('stg_campaign_recipient') }} cr
        on cr.campaign_id = sc.campaign_id
        and cr.list_id = sc.list_id
    inner join segment_members sm
        on sm.member_id = cr.member_id
        and sm.list_id = cr.list_id
    group by sm.segment_id, sm.list_id
),
campaign_activity as (
    select
        sm.segment_id,
        sm.list_id,
        count(*) filter (where cra.action = 'open')::BIGINT as campaign_opens,
        count(*) filter (where cra.action = 'click')::BIGINT as campaign_clicks,
        count(distinct (cra.campaign_id, cra.member_id)) filter (where cra.action = 'open')::BIGINT as campaign_unique_opens,
        count(distinct (cra.campaign_id, cra.member_id)) filter (where cra.action = 'click')::BIGINT as campaign_unique_clicks
    from sent_campaigns sc
    inner join {{ ref('stg_campaign_recipient_activity') }} cra
        on cra.campaign_id = sc.campaign_id
        and cra.list_id = sc.list_id
    inner join segment_members sm
        on sm.member_id = cra.member_id
        and sm.list_id = cra.list_id
    group by sm.segment_id, sm.list_id
),
campaign_unsubscribes as (
    select
        sm.segment_id,
        sm.list_id,
        count(*)::BIGINT as campaign_unsubscribes
    from sent_campaigns sc
    inner join {{ ref('stg_unsubscribe') }} u
        on u.campaign_id = sc.campaign_id
        and u.list_id = sc.list_id
    inner join segment_members sm
        on sm.member_id = u.member_id
        and sm.list_id = u.list_id
    group by sm.segment_id, sm.list_id
),
sent_automation_emails as (
    select distinct id as automation_email_id
    from {{ ref('stg_automation_email') }}
    where status = 'sent'
),
automation_sends as (
    select
        sm.segment_id,
        sm.list_id,
        count(*)::BIGINT as automation_sends
    from sent_automation_emails sae
    inner join {{ ref('stg_automation_recipient') }} ar
        on ar.automation_email_id = sae.automation_email_id
    inner join segment_members sm
        on sm.member_id = ar.member_id
        and sm.list_id = ar.list_id
    group by sm.segment_id, sm.list_id
),
automation_activity as (
    select
        sm.segment_id,
        sm.list_id,
        count(*) filter (where ara.action = 'open')::BIGINT as automation_opens,
        count(*) filter (where ara.action = 'click')::BIGINT as automation_clicks,
        count(distinct (ara.automation_email_id, ara.member_id)) filter (where ara.action = 'open')::BIGINT as automation_unique_opens,
        count(distinct (ara.automation_email_id, ara.member_id)) filter (where ara.action = 'click')::BIGINT as automation_unique_clicks,
        count(*) filter (where ara.action = 'unsubscribe')::BIGINT as automation_unsubscribes
    from sent_automation_emails sae
    inner join {{ ref('stg_automation_recipient_activity') }} ara
        on ara.automation_email_id = sae.automation_email_id
    inner join segment_members sm
        on sm.member_id = ara.member_id
        and sm.list_id = ara.list_id
    group by sm.segment_id, sm.list_id
)
select
    s.segment_id,
    s.list_id,
    l.name as list_name,
    s.member_count,
    s.segment_name,
    s.segment_type,
    s.updated_timestamp,
    s.created_timestamp,
    coalesce(cs.campaign_sends, 0)::BIGINT as campaign_sends,
    coalesce(ca.campaign_opens, 0)::BIGINT as campaign_opens,
    coalesce(ca.campaign_clicks, 0)::BIGINT as campaign_clicks,
    coalesce(ca.campaign_unique_opens, 0)::BIGINT as campaign_unique_opens,
    coalesce(ca.campaign_unique_clicks, 0)::BIGINT as campaign_unique_clicks,
    coalesce(cu.campaign_unsubscribes, 0)::BIGINT as campaign_unsubscribes,
    coalesce(ats.automation_sends, 0)::BIGINT as automation_sends,
    coalesce(ata.automation_opens, 0)::BIGINT as automation_opens,
    coalesce(ata.automation_clicks, 0)::BIGINT as automation_clicks,
    coalesce(ata.automation_unique_opens, 0)::BIGINT as automation_unique_opens,
    coalesce(ata.automation_unique_clicks, 0)::BIGINT as automation_unique_clicks,
    coalesce(ata.automation_unsubscribes, 0)::BIGINT as automation_unsubscribes
from segments s
left join {{ ref('stg_list') }} l
    on l.id = s.list_id
left join campaign_sends cs
    on cs.segment_id = s.segment_id
    and cs.list_id = s.list_id
left join campaign_activity ca
    on ca.segment_id = s.segment_id
    and ca.list_id = s.list_id
left join campaign_unsubscribes cu
    on cu.segment_id = s.segment_id
    and cu.list_id = s.list_id
left join automation_sends ats
    on ats.segment_id = s.segment_id
    and ats.list_id = s.list_id
left join automation_activity ata
    on ata.segment_id = s.segment_id
    and ata.list_id = s.list_id
