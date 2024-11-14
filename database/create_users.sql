CREATE TABLE `users` (
    `id`    INTEGER PRIMARY KEY AUTO_INCREMENT,
    `telegram_id`   BIGINT NOT NULL UNIQUE,
    `first_name`    TINYTEXT DEFAULT NULL,
    `last_name` TINYTEXT DEFAULT NULL,
    `is_admin`  BOOL DEFAULT FALSE,
    `used_bot`   BOOL DEFAULT FALSE,
    `blocked_bot`   BOOL DEFAULT FALSE,
    `created_at`    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `last_updated`  TIMESTAMP DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP
);