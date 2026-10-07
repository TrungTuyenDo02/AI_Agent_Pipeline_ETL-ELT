WITH task_base AS (
    SELECT
        id AS task_id,
        assignee_id AS assignee_user_id,
        completed AS is_completed,
        completed_at,
        created_at,
        due_on AS due_date,
        modified_at AS task_modified_at,
        name AS task_description,
        workspace_id,
        parent_id
    FROM {{ ref('stg_task') }}
),
story_dedup AS (
    SELECT DISTINCT
        id AS story_id,
        target_id
    FROM {{ ref('stg_story') }}
),
story_metrics AS (
    SELECT
        target_id AS task_id,
        COUNT(story_id)::BIGINT AS number_of_comments
    FROM story_dedup
    GROUP BY target_id
),
follower_dedup AS (
    SELECT DISTINCT
        task_id,
        user_id
    FROM {{ ref('stg_task_follower') }}
),
follower_metrics AS (
    SELECT
        task_id,
        COUNT(*)::BIGINT AS number_of_followers
    FROM follower_dedup
    GROUP BY task_id
),
task_tag_dedup AS (
    SELECT DISTINCT
        task_id,
        tag_id
    FROM {{ ref('stg_task_tag') }}
),
tag_links AS (
    SELECT DISTINCT
        task_tag.task_id,
        task_tag.tag_id,
        tag.name AS tag_name
    FROM task_tag_dedup AS task_tag
    INNER JOIN {{ ref('stg_tag') }} AS tag
        ON task_tag.tag_id = tag.id
),
tag_metrics AS (
    SELECT
        task_id,
        string_agg(tag_name, ', ' ORDER BY tag_name) AS tags,
        COUNT(*)::BIGINT AS number_of_tags
    FROM tag_links
    GROUP BY task_id
)
SELECT
    task_base.task_id,
    task_base.assignee_user_id,
    task_base.is_completed,
    task_base.completed_at,
    task_base.created_at,
    task_base.due_date,
    task_base.task_modified_at,
    task_base.task_description,
    task_base.workspace_id,
    CASE
        WHEN task_base.completed_at IS NULL THEN NULL
        ELSE date_diff('day', CAST(task_base.created_at AS TIMESTAMP), CAST(task_base.completed_at AS TIMESTAMP))::BIGINT
    END AS days_open,
    CASE WHEN task_base.assignee_user_id IS NOT NULL THEN 1 ELSE 0 END::BIGINT AS is_currently_assigned,
    CASE WHEN task_base.assignee_user_id IS NOT NULL THEN 1 ELSE 0 END::BIGINT AS has_been_assigned,
    COALESCE(story_metrics.number_of_comments, 0)::BIGINT AS number_of_comments,
    COALESCE(follower_metrics.number_of_followers, 0)::BIGINT AS number_of_followers,
    COALESCE(tag_metrics.tags, '') AS tags,
    COALESCE(tag_metrics.number_of_tags, 0)::BIGINT AS number_of_tags,
    CASE WHEN task_base.parent_id IS NOT NULL THEN 1 ELSE 0 END::BIGINT AS is_subtask
FROM task_base
LEFT JOIN story_metrics
    ON task_base.task_id = story_metrics.task_id
LEFT JOIN follower_metrics
    ON task_base.task_id = follower_metrics.task_id
LEFT JOIN tag_metrics
    ON task_base.task_id = tag_metrics.task_id
