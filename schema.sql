CREATE TABLE IF NOT EXISTS user_blacklist(
    id BIGINT UNIQUE,
    reason TEXT
);

CREATE TABLE IF NOT EXISTS guild_blacklist(
    id BIGINT UNIQUE,
    reason TEXT
);

CREATE TABLE IF NOT EXISTS levels(
    user_id BIGINT,
    guild_id BIGINT,
    lvl INT,
    xp BIGINT,
    cd REAL,
    color TEXT,
    bg TEXT
);