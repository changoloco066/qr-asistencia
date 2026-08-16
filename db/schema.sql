CREATE TABLE teachers (
    id              SERIAL PRIMARY KEY,
    username        VARCHAR(50) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL
);

CREATE TABLE students (
    matricula   VARCHAR(20) PRIMARY KEY,
    full_name   VARCHAR(120) NOT NULL
);

CREATE TABLE sessions (
    id            SERIAL PRIMARY KEY,
    session_date  DATE NOT NULL,
    created_at    TIMESTAMP DEFAULT now()
);

CREATE TABLE session_tokens (
    id          SERIAL PRIMARY KEY,
    session_id  INTEGER REFERENCES sessions(id),
    token       VARCHAR(64) NOT NULL,
    expires_at  TIMESTAMP NOT NULL
);

CREATE TABLE attendance (
    id              SERIAL PRIMARY KEY,
    session_id      INTEGER REFERENCES sessions(id),
    matricula       VARCHAR(20) REFERENCES students(matricula),
    checked_in_at   TIMESTAMP DEFAULT now(),
    UNIQUE (session_id, matricula)
);
