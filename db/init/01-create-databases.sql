-- Runs once, the first time the Postgres data volume is initialised.
-- Creates the separate database each stateful microservice expects.
CREATE DATABASE smartgrid_ingestion;
CREATE DATABASE smartgrid_collection;
CREATE DATABASE smartgrid_registration;
