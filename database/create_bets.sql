CREATE TABLE `bets` (
    `id`    INTEGER PRIMARY KEY AUTO_INCREMENT,
    `match_id`    MEDIUMINT,
    `user_id`    INTEGER,
    `bet` TINYTEXT,
    `logo`   MEDIUMBLOB DEFAULT NULL,
    `created_at`    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `last_updated_at`  TIMESTAMP DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`match_id`) REFERENCES matches (`api_id`),
    FOREIGN KEY (`user_id`) REFERENCES users (`id`)
);
