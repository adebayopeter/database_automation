-- Database Automation Suite - macOS Setup Script
-- This script creates the databases and test data needed for the automation suite on macOS

-- Create the main test database
DROP DATABASE IF EXISTS test_automation;
CREATE DATABASE test_automation;

-- Create the replica test database  
DROP DATABASE IF EXISTS replica_test_automation;
CREATE DATABASE replica_test_automation;

-- Connect to the main test database
\c test_automation;

-- Create test schema
CREATE SCHEMA IF NOT EXISTS automation;

-- Create test tables with realistic data structure
CREATE TABLE automation.test_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

CREATE TABLE automation.test_orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES automation.test_users(id) ON DELETE CASCADE,
    order_number VARCHAR(20) UNIQUE NOT NULL,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_amount DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    shipping_address TEXT,
    billing_address TEXT
);

CREATE TABLE automation.test_products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    category_id INTEGER,
    sku VARCHAR(50) UNIQUE,
    stock_quantity INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

CREATE TABLE automation.test_order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES automation.test_orders(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES automation.test_products(id),
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    total_price DECIMAL(10,2) NOT NULL
);

-- Create indexes for performance testing and monitoring
CREATE INDEX idx_users_email ON automation.test_users(email);
CREATE INDEX idx_users_username ON automation.test_users(username);
CREATE INDEX idx_users_created_at ON automation.test_users(created_at);
CREATE INDEX idx_orders_user_id ON automation.test_orders(user_id);
CREATE INDEX idx_orders_date ON automation.test_orders(order_date);
CREATE INDEX idx_orders_status ON automation.test_orders(status);
CREATE INDEX idx_products_category ON automation.test_products(category_id);
CREATE INDEX idx_products_sku ON automation.test_products(sku);
CREATE INDEX idx_order_items_order_id ON automation.test_order_items(order_id);
CREATE INDEX idx_order_items_product_id ON automation.test_order_items(product_id);

-- Insert sample users
INSERT INTO automation.test_users (username, email, first_name, last_name) VALUES
    ('admin', 'admin@example.com', 'System', 'Administrator'),
    ('john_doe', 'john.doe@example.com', 'John', 'Doe'),
    ('jane_smith', 'jane.smith@example.com', 'Jane', 'Smith'),
    ('bob_wilson', 'bob.wilson@example.com', 'Bob', 'Wilson'),
    ('alice_brown', 'alice.brown@example.com', 'Alice', 'Brown'),
    ('charlie_davis', 'charlie.davis@example.com', 'Charlie', 'Davis'),
    ('diana_miller', 'diana.miller@example.com', 'Diana', 'Miller'),
    ('frank_garcia', 'frank.garcia@example.com', 'Frank', 'Garcia'),
    ('grace_anderson', 'grace.anderson@example.com', 'Grace', 'Anderson'),
    ('henry_taylor', 'henry.taylor@example.com', 'Henry', 'Taylor');

-- Insert sample products
INSERT INTO automation.test_products (name, description, price, category_id, sku, stock_quantity) VALUES
    ('MacBook Pro M3', 'Apple MacBook Pro with M3 chip', 1999.99, 1, 'MBP-M3-001', 50),
    ('iPhone 15 Pro', 'Latest iPhone with Pro features', 999.99, 2, 'IPH-15P-001', 100),
    ('AirPods Pro', 'Wireless earbuds with noise cancellation', 249.99, 3, 'APP-GEN2-001', 200),
    ('iPad Air', 'Lightweight tablet for productivity', 599.99, 4, 'IPA-AIR-001', 75),
    ('Apple Watch Series 9', 'Advanced smartwatch', 399.99, 5, 'AWS-S9-001', 120),
    ('Magic Mouse', 'Wireless mouse for Mac', 79.99, 6, 'MM-WL-001', 300),
    ('Magic Keyboard', 'Wireless keyboard for Mac', 99.99, 6, 'MK-WL-001', 250),
    ('Studio Display', '27-inch 5K display', 1599.99, 7, 'SD-27-001', 25),
    ('Mac Studio', 'Compact pro desktop', 1999.99, 1, 'MS-M2U-001', 30),
    ('HomePod mini', 'Smart speaker', 99.99, 8, 'HPM-001', 150);

-- Generate sample orders with realistic patterns
INSERT INTO automation.test_orders (user_id, order_number, total_amount, status, shipping_address, billing_address)
SELECT 
    u.id,
    'ORD-' || LPAD((ROW_NUMBER() OVER())::text, 6, '0'),
    ROUND((RANDOM() * 2000 + 100)::numeric, 2),
    CASE 
        WHEN RANDOM() < 0.2 THEN 'pending'
        WHEN RANDOM() < 0.4 THEN 'processing'
        WHEN RANDOM() < 0.6 THEN 'shipped'
        WHEN RANDOM() < 0.8 THEN 'delivered'
        ELSE 'completed'
    END,
    u.first_name || ' ' || u.last_name || CHR(10) || 
    (FLOOR(RANDOM() * 9999) + 1)::text || ' Test St' || CHR(10) ||
    'Test City, TC ' || (FLOOR(RANDOM() * 90000) + 10000)::text,
    u.first_name || ' ' || u.last_name || CHR(10) || 
    (FLOOR(RANDOM() * 9999) + 1)::text || ' Test St' || CHR(10) ||
    'Test City, TC ' || (FLOOR(RANDOM() * 90000) + 10000)::text
FROM automation.test_users u
CROSS JOIN generate_series(1, 3) -- Each user gets 3 orders on average
WHERE RANDOM() < 0.8; -- Some randomness in order creation

-- Generate order items
INSERT INTO automation.test_order_items (order_id, product_id, quantity, unit_price, total_price)
SELECT 
    o.id,
    p.id,
    FLOOR(RANDOM() * 3) + 1 as quantity,
    p.price,
    (FLOOR(RANDOM() * 3) + 1) * p.price
FROM automation.test_orders o
CROSS JOIN automation.test_products p
WHERE RANDOM() < 0.3; -- Random selection of products per order

-- Create views for testing complex queries
CREATE VIEW automation.user_order_summary AS
SELECT 
    u.id,
    u.username,
    u.email,
    u.first_name || ' ' || u.last_name as full_name,
    COUNT(o.id) as order_count,
    COALESCE(SUM(o.total_amount), 0) as total_spent,
    MAX(o.order_date) as last_order_date,
    AVG(o.total_amount) as avg_order_value
FROM automation.test_users u
LEFT JOIN automation.test_orders o ON u.id = o.user_id
GROUP BY u.id, u.username, u.email, u.first_name, u.last_name;

CREATE VIEW automation.product_sales_summary AS
SELECT 
    p.id,
    p.name,
    p.sku,
    p.price,
    COUNT(oi.id) as times_ordered,
    COALESCE(SUM(oi.quantity), 0) as total_quantity_sold,
    COALESCE(SUM(oi.total_price), 0) as total_revenue
FROM automation.test_products p
LEFT JOIN automation.test_order_items oi ON p.id = oi.product_id
GROUP BY p.id, p.name, p.sku, p.price;

-- Create functions for testing
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
    random_user_id INTEGER;
    order_num TEXT;
BEGIN
    FOR i IN 1..user_count LOOP
        SELECT id INTO random_user_id 
        FROM automation.test_users 
        ORDER BY RANDOM() 
        LIMIT 1;
        
        order_num := 'BULK-' || LPAD(i::text, 6, '0');
        
        INSERT INTO automation.test_orders (user_id, order_number, total_amount, status)
        VALUES (
            random_user_id,
            order_num,
            ROUND((RANDOM() * 1000 + 50)::numeric, 2),
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

-- Create performance testing table with larger dataset
CREATE TABLE automation.performance_test (
    id SERIAL PRIMARY KEY,
    large_text TEXT,
    random_number INTEGER,
    category_code VARCHAR(10),
    score DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_processed BOOLEAN DEFAULT false
);

-- Insert performance test data
INSERT INTO automation.performance_test (large_text, random_number, category_code, score)
SELECT 
    'Performance test data row ' || generate_series || ' - ' || repeat('x', 500),
    (RANDOM() * 1000000)::INTEGER,
    'CAT' || LPAD((RANDOM() * 999 + 1)::INTEGER::text, 3, '0'),
    ROUND((RANDOM() * 100)::numeric, 2)
FROM generate_series(1, 25000);

-- Create indexes that might become fragmented over time
CREATE INDEX idx_performance_random ON automation.performance_test(random_number);
CREATE INDEX idx_performance_category ON automation.performance_test(category_code);
CREATE INDEX idx_performance_score ON automation.performance_test(score);
CREATE INDEX idx_performance_created_at ON automation.performance_test(created_at);

-- Enable query statistics collection
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Create monitoring user with appropriate permissions
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = 'automation_monitor') THEN
        CREATE USER automation_monitor WITH PASSWORD 'monitor_password123';
    END IF;
END
$$;

-- Grant necessary permissions for monitoring
GRANT CONNECT ON DATABASE test_automation TO automation_monitor;
GRANT USAGE ON SCHEMA automation TO automation_monitor;
GRANT SELECT ON ALL TABLES IN SCHEMA automation TO automation_monitor;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA automation TO automation_monitor;

-- Grant system monitoring permissions
GRANT pg_monitor TO automation_monitor;

-- Configure database settings for better monitoring
ALTER DATABASE test_automation SET log_statement = 'mod';
ALTER DATABASE test_automation SET log_min_duration_statement = 1000;
ALTER DATABASE test_automation SET track_activities = on;
ALTER DATABASE test_automation SET track_counts = on;

-- Setup replica database with basic structure
\c replica_test_automation;

-- Create the same schema structure in replica
CREATE SCHEMA IF NOT EXISTS automation;

-- Copy table structures (simplified for replica testing)
CREATE TABLE automation.test_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

-- Insert a small subset of data for replica testing
INSERT INTO automation.test_users (username, email) VALUES
    ('replica_admin', 'replica.admin@example.com'),
    ('replica_test', 'replica.test@example.com');

-- Grant permissions to monitoring user
GRANT CONNECT ON DATABASE replica_test_automation TO automation_monitor;
GRANT USAGE ON SCHEMA automation TO automation_monitor;
GRANT SELECT ON ALL TABLES IN SCHEMA automation TO automation_monitor;

-- Connect back to main database
\c test_automation;

-- Create a summary report
\echo '============================================'
\echo 'Database Setup Complete!'
\echo '============================================'
\echo 'Created databases:'
\echo '  - test_automation (main database)'
\echo '  - replica_test_automation (replica for testing)'
\echo ''
\echo 'Created schema: automation'
\echo ''
\echo 'Created tables:'
\echo '  - test_users (10 sample users)'
\echo '  - test_products (10 sample products)'  
\echo '  - test_orders (sample orders)'
\echo '  - test_order_items (order line items)'
\echo '  - performance_test (25,000 rows for testing)'
\echo ''
\echo 'Created monitoring user: automation_monitor'
\echo 'Password: monitor_password123'
\echo ''
\echo 'Sample data statistics:'
SELECT 'Users: ' || count(*) FROM automation.test_users;
SELECT 'Products: ' || count(*) FROM automation.test_products;  
SELECT 'Orders: ' || count(*) FROM automation.test_orders;
SELECT 'Order Items: ' || count(*) FROM automation.test_order_items;
SELECT 'Performance Test Records: ' || count(*) FROM automation.performance_test;
\echo ''
\echo 'Ready to test Database Automation Suite!'
\echo 'Run: python database_automation.py test'