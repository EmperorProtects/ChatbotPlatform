-- Initialize PostgreSQL for Chatbot Platform
-- This script runs when PostgreSQL container starts for the first time

-- Create chatbot user if not exists
-- CREATE USER IF NOT EXISTS chatbot_user WITH PASSWORD 'chatbot_pass';

-- Create main database
-- CREATE DATABASE chatbot_db OWNER chatbot_user;

-- Grant all privileges to user
GRANT ALL PRIVILEGES ON DATABASE chatbot_db TO chatbot_user;
ALTER USER chatbot_user CREATEDB;

-- Connect to chatbot_db to create auth tables
\c chatbot_db chatbot_user;

-- Create auth service tables
CREATE TABLE IF NOT EXISTS roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    permissions JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_superuser BOOLEAN DEFAULT false,
    last_login TIMESTAMP,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_roles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    assigned_by INTEGER REFERENCES users(id),
    UNIQUE(user_id, role_id)
);

CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    refresh_token VARCHAR(255) UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address INET,
    user_agent TEXT
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);
CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires ON user_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_user_roles_user_id ON user_roles(user_id);

-- Insert default roles
INSERT INTO roles (name, description, permissions) VALUES 
('admin', 'System Administrator', '{
    "users": ["create", "read", "update", "delete"],
    "roles": ["create", "read", "update", "delete"],
    "knowledge": ["create", "read", "update", "delete"],
    "briefs": ["create", "read", "update", "delete"],
    "analytics": ["read"],
    "settings": ["read", "update"],
    "system": ["admin"]
}'),
('manager', 'Content Manager', '{
    "knowledge": ["create", "read", "update", "delete"],
    "briefs": ["create", "read", "update", "delete"],
    "analytics": ["read"],
    "dialogs": ["read", "update"]
}'),
('operator', 'Chat Operator', '{
    "dialogs": ["read", "update"],
    "knowledge": ["read"],
    "briefs": ["read"]
}'),
('viewer', 'Read Only User', '{
    "knowledge": ["read"],
    "briefs": ["read"],
    "analytics": ["read"],
    "dialogs": ["read"]
}')
ON CONFLICT (name) DO NOTHING;

-- Insert default users (with bcrypt hashed passwords)
-- admin123 -> $2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj9QGkqKQUEO
-- manager123 -> $2b$12$8G3JZQX5LQMR.9J.4V5vSO5K5YrD5Kv5J5K5YrD5Kv5J5K5YrD5Kv  
-- operator123 -> $2b$12$9H4LAQY6MRNST0K.5W6wTO6L6ZsE6Lw6K6L6ZsE6Lw6K6L6ZsE6Lw
INSERT INTO users (username, email, full_name, hashed_password, is_superuser) VALUES 
('admin', 'admin@chatbot-platform.com', 'System Administrator', '$2a$12$ayr3QlsPLJBp..ip9smsCO3fICrBS0b1tUxUWEQUZ7TO1DNFPKV.q', true),
('manager', 'manager@chatbot-platform.com', 'Content Manager', '$2b$12$8G3JZQX5LQMR.9J.4V5vSO5K5YrD5Kv5J5K5YrD5Kv5J5K5YrD5Kv', false),
('operator', 'operator@chatbot-platform.com', 'Chat Operator', '$2b$12$9H4LAQY6MRNST0K.5W6wTO6L6ZsE6Lw6K6L6ZsE6Lw6K6L6ZsE6Lw', false)
ON CONFLICT (username) DO NOTHING;

-- Assign roles to users
INSERT INTO user_roles (user_id, role_id, assigned_by)
SELECT u.id, r.id, 1
FROM users u, roles r
WHERE (u.username = 'admin' AND r.name = 'admin')
   OR (u.username = 'manager' AND r.name = 'manager')
   OR (u.username = 'operator' AND r.name = 'operator')
ON CONFLICT (user_id, role_id) DO NOTHING;

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_roles_updated_at ON roles;
CREATE TRIGGER update_roles_updated_at 
    BEFORE UPDATE ON roles 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create function to clean expired sessions
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM user_sessions WHERE expires_at < CURRENT_TIMESTAMP;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Create function to get user with roles
CREATE OR REPLACE FUNCTION get_user_with_roles(user_id_param INTEGER)
RETURNS TABLE(
    id INTEGER,
    username VARCHAR,
    email VARCHAR,
    full_name VARCHAR,
    is_active BOOLEAN,
    is_superuser BOOLEAN,
    roles JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        u.id,
        u.username,
        u.email,
        u.full_name,
        u.is_active,
        u.is_superuser,
        COALESCE(
            jsonb_agg(
                jsonb_build_object(
                    'id', r.id,
                    'name', r.name,
                    'permissions', r.permissions
                )
            ) FILTER (WHERE r.id IS NOT NULL),
            '[]'::jsonb
        ) as roles
    FROM users u
    LEFT JOIN user_roles ur ON u.id = ur.user_id
    LEFT JOIN roles r ON ur.role_id = r.id
    WHERE u.id = user_id_param
    GROUP BY u.id, u.username, u.email, u.full_name, u.is_active, u.is_superuser;
END;
$$ LANGUAGE plpgsql;

-- Create view for easy user management
DROP VIEW IF EXISTS user_management;
CREATE VIEW user_management AS
SELECT 
    u.id,
    u.username,
    u.email,
    u.full_name,
    u.is_active,
    u.is_superuser,
    u.last_login,
    u.created_at,
    string_agg(DISTINCT r.name, ', ') as roles,
    jsonb_agg(DISTINCT r.permissions) FILTER (WHERE r.permissions IS NOT NULL) as permissions
FROM users u
LEFT JOIN user_roles ur ON u.id = ur.user_id
LEFT JOIN roles r ON ur.role_id = r.id
GROUP BY u.id, u.username, u.email, u.full_name, u.is_active, u.is_superuser, u.last_login, u.created_at;

-- Add comments
COMMENT ON TABLE users IS 'System users with authentication data';
COMMENT ON TABLE roles IS 'User roles with permissions';
COMMENT ON TABLE user_roles IS 'Many-to-many relationship between users and roles';
COMMENT ON TABLE user_sessions IS 'Active user sessions for token management';
COMMENT ON VIEW user_management IS 'Convenient view for user management operations';

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'Auth service database initialized successfully';
    RAISE NOTICE 'Default users: admin/admin123, manager/manager123, operator/operator123';
END $$;
