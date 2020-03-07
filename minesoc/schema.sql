CREATE TABLE IF NOT EXISTS user_blacklist(
    id BIGINT UNIQUE,
    reason TEXT
);

CREATE TABLE IF NOT EXISTS guild_blacklist(
    id BIGINT UNIQUE,
    reason TEXT
);

CREATE TABLE IF NOT EXISTS items(
    id SERIAL UNIQUE,
    name TEXT,
    price BIGINT,
    type INT
);

CREATE TABLE IF NOT EXISTS inventory(
    user_id BIGINT,
    inventory integer ARRAY
);