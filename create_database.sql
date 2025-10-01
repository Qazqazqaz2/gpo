-- Create PostgreSQL database for practice management system
-- Based on Flask SQLAlchemy models

-- Create database
CREATE DATABASE practice_management;

-- Connect to the database
\c practice_management;

-- Enable UUID extension if needed
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create tables
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(200) NOT NULL,
    role_id INTEGER REFERENCES roles(id)
);

CREATE TABLE cafedrals (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

CREATE TABLE directions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    cafedral_id INTEGER REFERENCES cafedrals(id)
);

CREATE TABLE groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    direction_id INTEGER REFERENCES directions(id)
);

CREATE TABLE students (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    surname VARCHAR(100) NOT NULL,
    patronymic VARCHAR(100) NOT NULL,
    group_id INTEGER NOT NULL REFERENCES groups(id)
);

CREATE TABLE practice_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

CREATE TABLE organizations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    address VARCHAR(200) NOT NULL
);

CREATE TABLE contracts (
    id SERIAL PRIMARY KEY,
    contract_number VARCHAR(100) NOT NULL,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    date_start TIMESTAMP,
    date_end TIMESTAMP
);

CREATE TABLE statuses (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL
);

CREATE TABLE practic_times (
    id SERIAL PRIMARY KEY,
    date_start TIMESTAMP,
    date_end TIMESTAMP,
    direction_id INTEGER NOT NULL REFERENCES directions(id)
);

CREATE TABLE ask_forms (
    id SERIAL PRIMARY KEY,
    practice_type INTEGER NOT NULL REFERENCES practice_types(id),
    group INTEGER NOT NULL REFERENCES groups(id),
    contract INTEGER NOT NULL REFERENCES contracts(id),
    ask_form_resposeble INTEGER NOT NULL REFERENCES users(id),
    consultant_leader INTEGER NOT NULL REFERENCES users(id),
    practice_leader INTEGER NOT NULL REFERENCES users(id),
    status INTEGER NOT NULL REFERENCES statuses(id),
    student INTEGER NOT NULL REFERENCES students(id)
);

CREATE TABLE fields (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    type VARCHAR(35) NOT NULL,
    block VARCHAR(255),
    page VARCHAR(255),
    text TEXT,
    mutability VARCHAR(255)
);

CREATE TABLE templates (
    id SERIAL PRIMARY KEY,
    template_body TEXT NOT NULL
);

-- Insert default data

-- Default roles
INSERT INTO roles (name) VALUES ('студент');
INSERT INTO roles (name) VALUES ('преподаватель');

-- Default statuses
INSERT INTO statuses (name) VALUES ('0'); -- pending/rejected
INSERT INTO statuses (name) VALUES ('1'); -- in review
INSERT INTO statuses (name) VALUES ('2'); -- approved
INSERT INTO statuses (name) VALUES ('3'); -- completed

-- Default cafedral
INSERT INTO cafedrals (name) VALUES ('ФСУ');
INSERT INTO cafedrals (name) VALUES ('АОИ');
INSERT INTO cafedrals (name) VALUES ('ИСР');
INSERT INTO cafedrals (name) VALUES ('ИСЭ');
INSERT INTO cafedrals (name) VALUES ('КИБЭВС');

-- Default directions
INSERT INTO directions (name, cafedral_id) 
VALUES ('Программная инженерия', (SELECT id FROM cafedrals WHERE name = 'ФСУ'));
INSERT INTO directions (name, cafedral_id) 
VALUES ('Информационные системы', (SELECT id FROM cafedrals WHERE name = 'АОИ'));
INSERT INTO directions (name, cafedral_id) 
VALUES ('Управление в технических системах', (SELECT id FROM cafedrals WHERE name = 'ИСЭ'));
INSERT INTO directions (name, cafedral_id) 
VALUES ('Информационная безопасность', (SELECT id FROM cafedrals WHERE name = 'КИБЭВС'));
INSERT INTO directions (name, cafedral_id) 
VALUES ('Социальная работа', (SELECT id FROM cafedrals WHERE name = 'ИСР'));

-- Default group
INSERT INTO groups (name, direction_id) 
VALUES ('722-1', (SELECT id FROM directions WHERE name = 'Программная инженерия'));

-- Default practice types
INSERT INTO practice_types (name) VALUES ('Учебная');
INSERT INTO practice_types (name) VALUES ('Преддипломная');
INSERT INTO practice_types (name) VALUES ('Производственная');

-- Default organization
INSERT INTO organizations (name, address) VALUES ('ТУСУР', 'г. Томск, пр. Ленина, 40');

-- Default contracts
INSERT INTO contracts (contract_number, organization_id) 
VALUES ('Заявление', (SELECT id FROM organizations WHERE name = 'ТУСУР'));
INSERT INTO contracts (contract_number, organization_id) 
VALUES ('Договор', (SELECT id FROM organizations WHERE name = 'ТУСУР'));

-- Default teacher users (password hash is for 'password')
INSERT INTO users (username, password_hash, role_id) 
VALUES ('Руководитель П. П.', 'pbkdf2:sha256:150000$xxxxxxxx$yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy', 
       (SELECT id FROM roles WHERE name = 'преподаватель'));
INSERT INTO users (username, password_hash, role_id) 
VALUES ('Руководитель Р. Р.', 'pbkdf2:sha256:150000$xxxxxxxx$yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy', 
       (SELECT id FROM roles WHERE name = 'преподаватель'));

-- Add indexes for performance
CREATE INDEX idx_users_role_id ON users(role_id);
CREATE INDEX idx_students_group_id ON students(group_id);
CREATE INDEX idx_groups_direction_id ON groups(direction_id);
CREATE INDEX idx_directions_cafedral_id ON directions(cafedral_id);
CREATE INDEX idx_contracts_organization_id ON contracts(organization_id);
CREATE INDEX idx_practic_times_direction_id ON practic_times(direction_id);
CREATE INDEX idx_ask_forms_practice_type ON ask_forms(practice_type);
CREATE INDEX idx_ask_forms_group ON ask_forms(group);
CREATE INDEX idx_ask_forms_contract ON ask_forms(contract);
CREATE INDEX idx_ask_forms_status ON ask_forms(status);
CREATE INDEX idx_ask_forms_student ON ask_forms(student);

-- Grant permissions if needed
-- GRANT ALL PRIVILEGES ON DATABASE practice_management TO your_user;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO your_user; 