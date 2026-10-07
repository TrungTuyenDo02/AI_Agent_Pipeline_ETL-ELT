SELECT
    CAST(id AS VARCHAR) AS list_id,
    CAST(date_created AS DATE) AS date_created,
    CAST(beamer_address AS VARCHAR) AS beamer_address,
    CAST(contact_address_1 AS VARCHAR) AS contact_address_1,
    CAST(contact_city AS VARCHAR) AS contact_city,
    CAST(contact_company AS VARCHAR) AS contact_company,
    CAST(contact_country AS VARCHAR) AS contact_country,
    CAST(contact_state AS VARCHAR) AS contact_state,
    CAST(contact_zip AS VARCHAR) AS contact_zip,
    CAST(default_from_email AS VARCHAR) AS default_from_email,
    CAST(default_from_name AS VARCHAR) AS default_from_name,
    CAST(default_language AS VARCHAR) AS default_language,
    CAST(email_type_option AS VARCHAR) AS email_type_option,
    CAST(list_rating AS DOUBLE) AS list_rating,
    CAST(name AS VARCHAR) AS name,
    CAST(permission_reminder AS VARCHAR) AS permission_reminder,
    CAST(subscribe_url_long AS VARCHAR) AS subscribe_url_long,
    CAST(subscribe_url_short AS VARCHAR) AS subscribe_url_short,
    CAST(use_archive_bar AS VARCHAR) AS use_archive_bar,
    CAST(visibility AS VARCHAR) AS visibility
FROM {{ source('raw', 'list') }}
WHERE _fivetran_deleted = FALSE
