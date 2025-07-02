-- Database Automation Suite - PostgreSQL Initialization Script
-- This script sets up test data and configurations for the automation suite

-- Create additional databases for testing
CREATE DATABASE automation_test;
CREATE DATABASE backup_test;

-- Connect to the automation test database
\c automation_test;

-- Create test schema
CREATE SCHEMA IF NOT EXISTS automation;

-- Create test tables
CREATE TABLE automation.test_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE automation.test_orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES automation.test_users(id),
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_amount DECIMAL(10,2),
    status VARCHAR(20) DEFAULT 'pending'
);

CREATE TABLE automation.test_products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price DECIMAL(10,2),
    category_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for testing index monitoring
CREATE INDEX idx_users_email ON automation.test_users(email);
CREATE INDEX idx_orders_user_id ON automation.test_orders(user_id);
CREATE INDEX idx_orders_date ON automation.test_orders(order_date);
CREATE INDEX idx_products_category ON automation.test_products(category_id);

-- Insert test data
INSERT INTO automation.test_users (username, email) VALUES
    ('admin', 'admin@example.com'),
    ('testuser1', 'user1@example.com'),
    ('testuser2', 'user2@example.com'),
    ('dbadmin', 'dba@example.com'),
    ('monitoring', 'monitoring@example.com');

INSERT INTO automation.test_products (name, description, price, category_id) VALUES
    ('Laptop', 'High-performance laptop', 999.99, 1),
    ('Mouse', 'Wireless mouse', 29.99, 2),
    ('Keyboard', 'Mechanical keyboard', 79.99, 2),
    ('Monitor', '27-inch 4K monitor', 399.99, 3),
    ('Webcam', 'HD webcam', 59.99, 4);

INSERT INTO automation.test_orders (user_id, total_amount, status) VALUES
    (1, 999.99, 'completed'),
    (2, 109.98, 'processing'),
    (3, 399.99, 'shipped'),
    (1, 59.99, 'pending'),
    (4, 79.99, 'completed');

-- Create a view for testing
CREATE VIEW automation.user_order_summary AS
SELECT 
    u.username,
    u.email,
    COUNT(o.id) as order_count,
    COALESCE(SUM(o.total_amount), 0) as total_spent
FROM automation.test_users u
LEFT JOIN automation.test_orders o ON u.id = o.user_id
GROUP BY u.id, u.username, u.email;

-- Create a function for testing
CREATE OR REPLACE FUNCTION automation.update_user_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger
CREATE TRIGGER update_user_timestamp_trigger
    BEFORE UPDATE ON automation.test_users
    FOR EACH ROW
    EXECUTE FUNCTION automation.update_user_timestamp();

-- Create stored procedure for bulk operations (testing performance optimization)
CREATE OR REPLACE FUNCTION automation.bulk_insert_orders(user_count INTEGER)
RETURNS VOID AS $$
DECLARE
    i INTEGER;
BEGIN
    FOR i IN 1..user_count LOOP
        INSERT INTO automation.test_orders (user_id, total_amount, status)
        VALUES (
            (SELECT id FROM automation.test_users ORDER BY RANDOM() LIMIT 1),
            ROUND((RANDOM() * 1000)::numeric, 2),
            CASE 
                WHEN RANDOM() < 0.3 THEN 'pending'
                WHEN RANDOM() < 0.6 THEN 'processing'
                WHEN RANDOM() < 0.9 THEN 'shipped'
                ELSE 'completed'
            END
        );
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Create monitoring user with limited privileges
CREATE USER automation_monitor WITH PASSWORD 'monitor_password';

-- Grant necessary permissions for monitoring
GRANT CONNECT ON DATABASE automation_test TO automation_monitor;
GRANT USAGE ON SCHEMA automation TO automation_monitor;
GRANT SELECT ON ALL TABLES IN SCHEMA automation TO automation_monitor;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA automation TO automation_monitor;

-- Grant system monitoring permissions
GRANT pg_monitor TO automation_monitor;

-- Enable query statistics collection
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Configure connection limits
ALTER DATABASE automation_test SET log_statement = 'all';
ALTER DATABASE automation_test SET log_min_duration_statement = 1000;

-- Create backup test database
\c backup_test;

CREATE TABLE backup_test_data (
    id SERIAL PRIMARY KEY,
    data TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert some test data for backup testing
INSERT INTO backup_test_data (data)
SELECT 'Test data row ' || generate_series(1, 1000);

-- Connect back to main database
\c automation_test;

-- Create additional test scenarios

-- Long-running query simulation table
CREATE TABLE automation.performance_test (
    id SERIAL PRIMARY KEY,
    large_text TEXT,
    random_number INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert data for performance testing
INSERT INTO automation.performance_test (large_text, random_number)
SELECT 
    repeat('x', 1000) || ' test data ' || generate_series(1, 10000),
    (RANDOM() * 1000000)::INTEGER
FROM generate_series(1, 10000);

-- Create an index that might become fragmented
CREATE INDEX idx_performance_random ON automation.performance_test(random_number);

-- Grant permissions for automation user
GRANT ALL PRIVILEGES ON SCHEMA automation TO automation_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA automation TO automation_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA automation TO automation_user;

-- Final message
\echo 'Database initialization completed successfully!'
\echo 'Created test databases: automation_test, backup_test'
\echo 'Created test schema: automation'
\echo 'Created monitoring user: automation_monitor'
\echo 'Inserted test data for automation testing'