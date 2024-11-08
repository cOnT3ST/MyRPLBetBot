CREATE TABLE `leagues` (
    `api_id`    INTEGER PRIMARY KEY,
    `league_country`    TINYTEXT DEFAULT NULL,
    `league_name`    TINYTEXT DEFAULT NULL,
    `logo_url` TEXT DEFAULT NULL,
    `logo`   MEDIUMBLOB DEFAULT NULL,
    `league_country_ru`    TINYTEXT DEFAULT NULL,
    `league_name_ru`    TINYTEXT DEFAULT NULL,
    `created_at`    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `last_updated_at`  TIMESTAMP DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP
);
