CREATE TABLE `bet_contests` (
    `id`    SMALLINT PRIMARY KEY AUTO_INCREMENT,
    `season_id`    INTEGER,
    `start_date`    TIMESTAMP,
    `end_date`    TIMESTAMP,
    `is_active` BOOL DEFAULT TRUE,
    `created_at`    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `last_updated_at`  TIMESTAMP DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`season_id`) REFERENCES seasons (`id`)
);
