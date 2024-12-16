CREATE TABLE `seasons` (
    `id`    INTEGER PRIMARY KEY AUTO_INCREMENT,
    `league_api_id`    INTEGER NOT NULL,
    `year`    SMALLINT NOT NULL,
    `end_year`    SMALLINT,
    `start_date`    DATE,
    `end_date`    DATE,
    `active` BOOL DEFAULT FALSE,
    `finished` BOOL DEFAULT FALSE,
    `start_datetime` DATETIME DEFAULT NULL,
    `end_datetime` DATETIME DEFAULT NULL,
    `created_at`    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `last_updated_at`  TIMESTAMP DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`league_api_id`) REFERENCES leagues (`api_id`)
);
