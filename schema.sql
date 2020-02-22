CREATE TABLE IF NOT EXISTS user_blacklist(
    id BIGINT UNIQUE,
    reason TEXT
);

CREATE TABLE IF NOT EXISTS guild_blacklist(
    id BIGINT UNIQUE,
    reason TEXT
);