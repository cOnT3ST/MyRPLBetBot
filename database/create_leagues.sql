CREATE TABLE `leagues` (
    `api_id`    INTEGER PRIMARY KEY,
    `league_country`    TINYTEXT,
    `league_name`    TINYTEXT,
    `logo_url` TEXT,
    `logo`   MEDIUMBLOB DEFAULT NULL,
    `league_country_ru`    TINYTEXT DEFAULT NULL,
    `league_name_ru`    TINYTEXT DEFAULT NULL,
    `created_at`    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `last_updated_at`  TIMESTAMP DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP
);
