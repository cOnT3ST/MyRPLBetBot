CREATE TABLE `teams` (
    `api_id`    SMALLINT PRIMARY KEY,
    `name`  TINYTEXT,
    `city`    TINYTEXT,
    `logo_url`    TEXT,
    `logo` MEDIUMBLOB DEFAULT NULL,
    `name_ru`  TINYTEXT DEFAULT NULL,
    `city_ru`    TINYTEXT DEFAULT NULL,
    `created_at`    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `last_updated_at`  TIMESTAMP DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP
);
