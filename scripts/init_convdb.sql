-- =============================
-- Dialog Service Database Init
-- =============================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================
-- Conversations
-- =============================

CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- связь с auth сервисом (без FK!)
    user_id BIGINT NOT NULL,

    status VARCHAR(20) DEFAULT 'enabled', -- open | closed
    channel VARCHAR(50), -- whatsapp | email | web | api


    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_conversations_user_id 
    ON conversations(user_id);

CREATE INDEX IF NOT EXISTS idx_conversations_status 
    ON conversations(status);

CREATE INDEX IF NOT EXISTS idx_conversations_created_at 
    ON conversations(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_conversations_updated_at 
    ON conversations(updated_at DESC);


-- =============================
-- Messages
-- =============================

CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    conversation_id UUID NOT NULL 
        REFERENCES conversations(id) ON DELETE CASCADE,

    sender_type VARCHAR(20) NOT NULL, 
    -- user | operator | bot | system

    message TEXT NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_id 
    ON messages(conversation_id);

CREATE INDEX IF NOT EXISTS idx_messages_created_at 
    ON messages(created_at);

CREATE INDEX IF NOT EXISTS idx_messages_sender_type 
    ON messages(sender_type);


-- =============================
-- Attachments (optional)
-- =============================

CREATE TABLE IF NOT EXISTS attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    message_id UUID 
        REFERENCES messages(id) ON DELETE CASCADE,

    file_url TEXT NOT NULL,
    file_type VARCHAR(50),
    file_size INTEGER,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_attachments_message_id 
    ON attachments(message_id);


-- =============================
-- Trigger: auto update updated_at
-- =============================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_conversations_updated_at 
    ON conversations;

CREATE TRIGGER update_conversations_updated_at
    BEFORE UPDATE ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- =============================
-- View: conversation with last message
-- =============================

DROP VIEW IF EXISTS conversation_with_last_message;

CREATE VIEW conversation_with_last_message AS
SELECT 
    c.*,
    m.message AS last_message,
    m.created_at AS last_message_time
FROM conversations c
LEFT JOIN LATERAL (
    SELECT message, created_at
    FROM messages
    WHERE conversation_id = c.id
    ORDER BY created_at DESC
    LIMIT 1
) m ON true;


-- =============================
-- Useful Functions
-- =============================

-- Close conversation
CREATE OR REPLACE FUNCTION close_conversation(conv_id UUID)
RETURNS VOID AS $$
BEGIN
    UPDATE conversations
    SET status = 'closed',
        closed_at = CURRENT_TIMESTAMP
    WHERE id = conv_id;
END;
$$ LANGUAGE plpgsql;

-- Reopen conversation
CREATE OR REPLACE FUNCTION reopen_conversation(conv_id UUID)
RETURNS VOID AS $$
BEGIN
    UPDATE conversations
    SET status = 'open',
        closed_at = NULL
    WHERE id = conv_id;
END;
$$ LANGUAGE plpgsql;


-- =============================
-- Done
-- =============================

DO $$
BEGIN
    RAISE NOTICE 'Dialog service database initialized successfully';
END $$;
