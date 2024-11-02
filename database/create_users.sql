CREATE TABLE `users` (
    `id`    INTEGER PRIMARY KEY AUTO_INCREMENT,
    `first_name`    TEXT DEFAULT NULL,
    `last_name` TEXT DEFAULT NULL,
    `telegram_id`   BIGINT NOT NULL UNIQUE,
    `is_admin`  BOOL DEFAULT FALSE,
    `used_bot`   BOOL DEFAULT FALSE,
    `blocked_bot`   BOOL DEFAULT FALSE,
    `created_at`    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `last_updated`  TIMESTAMP DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP
);