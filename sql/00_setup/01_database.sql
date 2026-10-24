-- target_db: master
-- Reference pattern: sql/00_setup/01_database.sql
-- Creates the serverless database once. UTF-8 collation avoids CSV encoding warnings.
IF NOT EXISTS (SELECT 1 FROM sys.databases WHERE name = '{{database}}')
    EXEC('CREATE DATABASE {{database}} COLLATE Latin1_General_100_BIN2_UTF8');
