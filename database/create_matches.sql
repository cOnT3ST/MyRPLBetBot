CREATE TABLE `matches` (
    `api_id`    MEDIUMINT PRIMARY KEY,
    `league_api_id`  INTEGER,
    `start_datetime`    TIMESTAMP,
    `round`    TINYINT,
    `home_team_id` SMALLINT,
    `away_team_id` SMALLINT,
    `score`    TINYTEXT DEFAULT NULL,
    `status_long`    TINYTEXT DEFAULT NULL,
    `status_short`    TINYTEXT DEFAULT NULL,
    `created_at`    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `last_updated_at`  TIMESTAMP DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`league_api_id`) REFERENCES leagues (`api_id`),
    FOREIGN KEY (`home_team_id`) REFERENCES teams (`api_id`),
    FOREIGN KEY (`away_team_id`) REFERENCES teams (`api_id`)
);
