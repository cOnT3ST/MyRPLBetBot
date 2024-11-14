CREATE TABLE `seasons` (
    `id`    INTEGER PRIMARY KEY AUTO_INCREMENT,
    `league_api_id`    INTEGER,
    `year`    SMALLINT,
    `end_year`    SMALLINT,
    `start_date`    TIMESTAMP,
    `end_date`    TIMESTAMP,
    `is_active` BOOL DEFAULT FALSE,
    `created_at`    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `last_updated_at`  TIMESTAMP DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`league_api_id`) REFERENCES leagues (`api_id`)
);
