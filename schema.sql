-- Run this in pgAdmin Query Tool for the 'smart_timetable' database

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'student'
);

CREATE TABLE IF NOT EXISTS timetable (
    id SERIAL PRIMARY KEY,
    course_code VARCHAR(50),
    semester VARCHAR(50),
    group_name VARCHAR(50),
    subject_code VARCHAR(50),
    subject_name VARCHAR(200),
    class_type VARCHAR(50),
    day VARCHAR(20),
    start_time TIME,
    end_time TIME,
    room VARCHAR(100),
    lecturer_name VARCHAR(200)
);

-- Insert a default admin user (password is 'admin123')
-- The password hash here is manually generated for 'admin123' using Werkzeug's pbkdf2:sha256 method
INSERT INTO users (name, email, password_hash, role) 
VALUES ('System Admin', 'admin@utem.edu.my', 'scrypt:32768:8:1$Cih4oV3E$38c7f991bb9518d8d32d0c242c1626f2129c5427f7140b01633cd58525e985873919e95315f6ee4f82d2757f4955f26938dc8f4d9b626d7054f96d2e67df4841', 'admin')
ON CONFLICT (email) DO NOTHING;
