CREATE TABLE IF NOT EXISTS user_blacklist(
    id BIGINT UNIQUE,
    reason TEXT
);

CREATE TABLE IF NOT EXISTS guild_blacklist(
    id BIGINT UNIQUE,
    reason TEXT
);

CREATE TABLE IF NOT EXISTS economy(
    user_id BIGINT UNIQUE,
    amount BIGINT,
    cd REAL,
    streak BIGINT,
    streak_time REAL,
    streak_cd REAL
);

CREATE TABLE IF NOT EXISTS items(
    id SERIAL UNIQUE,
    name TEXT,
    price BIGINT,
    type INT
);

CREATE TABLE IF NOT EXISTS inventory(
    user_id BIGINT UNIQUE,
    items INTEGER[]
);