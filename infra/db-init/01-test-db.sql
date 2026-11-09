-- Runs once, on the first start of an empty Postgres volume.
-- A separate database for the integration tests, so tests never touch dev data.
CREATE DATABASE swr_test;
\c swr
CREATE EXTENSION IF NOT EXISTS vector;
\c swr_test
CREATE EXTENSION IF NOT EXISTS vector;
