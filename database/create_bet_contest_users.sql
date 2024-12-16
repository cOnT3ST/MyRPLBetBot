CREATE TABLE `bet_contest_users` (
    `bet_contest_id`    SMALLINT NOT NULL,
    `user_id`    INTEGER NOT NULL,
    PRIMARY KEY (`bet_contest_id`, `user_id`),
    FOREIGN KEY (`bet_contest_id`) REFERENCES bet_contests (`id`),
    FOREIGN KEY (`user_id`) REFERENCES users (`id`)
);