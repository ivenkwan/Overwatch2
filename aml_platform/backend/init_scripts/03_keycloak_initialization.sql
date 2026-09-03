-- Disable ON_ERROR_STOP to gracefully ignore if role/database already mapping exists
\set ON_ERROR_STOP 0

-- Create the Keycloak role
CREATE ROLE keycloak LOGIN PASSWORD 'keycloak';

-- Create the Keycloak database
CREATE DATABASE keycloak OWNER keycloak;

-- Resume normal error handling
\set ON_ERROR_STOP 1
