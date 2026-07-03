"""initial_schema — объединение всех 16 миграций в одну идемпотентную

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-07-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- 001_initial_schema.sql ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            full_name TEXT,
            avatar_url TEXT,
            email_verified BOOLEAN DEFAULT FALSE,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            last_login_at TIMESTAMP WITH TIME ZONE
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);")

    op.execute("""
        CREATE TABLE IF NOT EXISTS user_api_keys (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            provider TEXT NOT NULL,
            provider_display_name TEXT,
            name TEXT,
            api_key_encrypted TEXT NOT NULL,
            model_preference TEXT DEFAULT 'auto',
            is_default BOOLEAN DEFAULT FALSE,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            last_used_at TIMESTAMP WITH TIME ZONE,
            CONSTRAINT check_provider CHECK (provider IN (
                'openrouter', 'google', 'openai', 'anthropic',
                'groq', 'ollama', 'gemini', 'gigachat'
            ))
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_keys_user_id ON user_api_keys(user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_keys_provider ON user_api_keys(provider);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_keys_active ON user_api_keys(is_active);")

    op.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            title TEXT,
            model_used TEXT,
            provider_used TEXT,
            message_count INTEGER DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            last_message_at TIMESTAMP WITH TIME ZONE
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON chat_sessions(user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON chat_sessions(created_at);")

    op.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
            role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
            content TEXT NOT NULL,
            metadata JSONB DEFAULT '{}',
            token_count INTEGER,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            CONSTRAINT fk_session FOREIGN KEY (session_id)
                REFERENCES chat_sessions(id) ON DELETE CASCADE
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_messages_session_id ON chat_messages(session_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_messages_created_at ON chat_messages(created_at);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_messages_role ON chat_messages(role);")

    op.execute("""
        CREATE TABLE IF NOT EXISTS provider_configs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            provider TEXT UNIQUE NOT NULL,
            enabled BOOLEAN DEFAULT FALSE,
            api_key_encrypted TEXT,
            model_default TEXT,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        DROP TRIGGER IF EXISTS update_users_updated_at ON users;
        CREATE TRIGGER update_users_updated_at
            BEFORE UPDATE ON users
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)
    op.execute("""
        DROP TRIGGER IF EXISTS update_user_api_keys_updated_at ON user_api_keys;
        CREATE TRIGGER update_user_api_keys_updated_at
            BEFORE UPDATE ON user_api_keys
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)
    op.execute("""
        DROP TRIGGER IF EXISTS update_chat_sessions_updated_at ON chat_sessions;
        CREATE TRIGGER update_chat_sessions_updated_at
            BEFORE UPDATE ON chat_sessions
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)

    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE user_api_keys ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;")

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='users_view_own' AND tablename='users') THEN
                CREATE POLICY "users_view_own" ON users FOR SELECT USING (auth.uid() = id);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='users_insert_own' AND tablename='users') THEN
                CREATE POLICY "users_insert_own" ON users FOR INSERT WITH CHECK (auth.uid() = id);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='users_update_own' AND tablename='users') THEN
                CREATE POLICY "users_update_own" ON users FOR UPDATE USING (auth.uid() = id);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='users_view_all_authenticated' AND tablename='users') THEN
                CREATE POLICY "users_view_all_authenticated" ON users FOR SELECT TO authenticated USING (true);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='users_service_all' AND tablename='users') THEN
                CREATE POLICY "users_service_all" ON users FOR ALL USING (true) WITH CHECK (true);
            END IF;
        END $$;
    """)

    # --- 004_user_settings_and_dialogs.sql ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID UNIQUE REFERENCES users(id) ON DELETE CASCADE,
            persona_tone VARCHAR(50) DEFAULT 'friendly',
            persona_detail_level VARCHAR(50) DEFAULT 'moderate',
            persona_emotion_level VARCHAR(50) DEFAULT 'balanced',
            persona_specialization VARCHAR(50) DEFAULT 'general',
            notification_email BOOLEAN DEFAULT true,
            notification_push BOOLEAN DEFAULT false,
            notification_sound BOOLEAN DEFAULT true,
            notification_frequency VARCHAR(20) DEFAULT 'immediate',
            theme VARCHAR(20) DEFAULT 'dark',
            font_size VARCHAR(10) DEFAULT 'medium',
            compact_mode BOOLEAN DEFAULT false,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_user_settings_user_id ON user_settings(user_id);")

    op.execute("""
        CREATE TABLE IF NOT EXISTS dialogs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            title VARCHAR(255),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            message_count INTEGER DEFAULT 0,
            is_favorite BOOLEAN DEFAULT false,
            last_message_at TIMESTAMP WITH TIME ZONE
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_dialogs_user_id ON dialogs(user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_dialogs_created_at ON dialogs(created_at);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_dialogs_updated_at ON dialogs(updated_at);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_dialogs_favorite ON dialogs(is_favorite);")

    op.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            dialog_id UUID REFERENCES dialogs(id) ON DELETE CASCADE,
            role VARCHAR(20) CHECK (role IN ('user', 'assistant')),
            content TEXT NOT NULL,
            model VARCHAR(100),
            provider VARCHAR(50),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            metadata JSONB DEFAULT '{}',
            CONSTRAINT fk_dialog FOREIGN KEY (dialog_id)
                REFERENCES dialogs(id) ON DELETE CASCADE
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_messages_dialog_id ON messages(dialog_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_messages_role ON messages(role);")
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_messages_content_fts
        ON messages USING gin(to_tsvector('russian', content));
    """)

    op.execute("""
        DROP TRIGGER IF EXISTS update_user_settings_updated_at ON user_settings;
        CREATE TRIGGER update_user_settings_updated_at
            BEFORE UPDATE ON user_settings
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)
    op.execute("""
        DROP TRIGGER IF EXISTS update_dialogs_updated_at ON dialogs;
        CREATE TRIGGER update_dialogs_updated_at
            BEFORE UPDATE ON dialogs
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION update_dialog_stats()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                UPDATE dialogs
                SET message_count = message_count + 1,
                    last_message_at = NEW.created_at,
                    updated_at = NOW()
                WHERE id = NEW.dialog_id;
            ELSIF TG_OP = 'DELETE' THEN
                UPDATE dialogs
                SET message_count = message_count - 1,
                    updated_at = NOW()
                WHERE id = OLD.dialog_id;
                UPDATE dialogs d
                SET last_message_at = (
                    SELECT MAX(m.created_at) FROM messages m WHERE m.dialog_id = d.id
                )
                WHERE d.id = OLD.dialog_id;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        DROP TRIGGER IF EXISTS update_dialog_stats_after_insert ON messages;
        CREATE TRIGGER update_dialog_stats_after_insert
            AFTER INSERT ON messages
            FOR EACH ROW
            EXECUTE FUNCTION update_dialog_stats();
    """)
    op.execute("""
        DROP TRIGGER IF EXISTS update_dialog_stats_after_delete ON messages;
        CREATE TRIGGER update_dialog_stats_after_delete
            AFTER DELETE ON messages
            FOR EACH ROW
            EXECUTE FUNCTION update_dialog_stats();
    """)

    op.execute("ALTER TABLE user_settings ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE dialogs ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE messages ENABLE ROW LEVEL SECURITY;")

    # --- 005_documents_and_collections.sql ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            title TEXT,
            filename TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_size BIGINT NOT NULL,
            file_url TEXT,
            file_path TEXT,
            collection_id UUID,
            status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
            tags TEXT[] DEFAULT '{}',
            summary TEXT,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_documents_collection_id ON documents(collection_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at);")

    op.execute("""
        CREATE TABLE IF NOT EXISTS document_collections (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_document_collections_user_id ON document_collections(user_id);")

    op.execute("""
        DROP TRIGGER IF EXISTS update_documents_updated_at ON documents;
        CREATE TRIGGER update_documents_updated_at
            BEFORE UPDATE ON documents
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)
    op.execute("""
        DROP TRIGGER IF EXISTS update_document_collections_updated_at ON document_collections;
        CREATE TRIGGER update_document_collections_updated_at
            BEFORE UPDATE ON document_collections
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)

    op.execute("ALTER TABLE documents ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE document_collections ENABLE ROW LEVEL SECURITY;")

    # --- 006_fix_rls_and_auth.sql ---
    op.execute("""
        CREATE OR REPLACE FUNCTION public.create_user_settings()
        RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO public.user_settings (user_id)
            VALUES (NEW.id)
            ON CONFLICT (user_id) DO NOTHING;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)
    op.execute("""
        DROP TRIGGER IF EXISTS on_user_created ON users;
        CREATE TRIGGER on_user_created
            AFTER INSERT ON users
            FOR EACH ROW
            EXECUTE FUNCTION public.create_user_settings();
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION public.check_tables_exist()
        RETURNS TABLE (table_name TEXT, table_exists BOOLEAN) AS $$
        BEGIN
            RETURN QUERY
            SELECT t.table_name,
                EXISTS(
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = t.table_name
                ) as table_exists
            FROM (VALUES
                ('users'::TEXT), ('user_api_keys'::TEXT),
                ('chat_sessions'::TEXT), ('chat_messages'::TEXT),
                ('user_settings'::TEXT), ('dialogs'::TEXT),
                ('messages'::TEXT)
            ) AS t(table_name);
        END;
        $$ LANGUAGE plpgsql;
    """)

    # --- 015_xray_traces.sql ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS xray_traces (
            trace_id        UUID PRIMARY KEY,
            user_message    TEXT NOT NULL,
            response        TEXT,
            strategy        TEXT NOT NULL DEFAULT 'simple',
            intent          TEXT,
            provider        TEXT,
            model           TEXT,
            total_ms        FLOAT NOT NULL DEFAULT 0,
            success         BOOLEAN NOT NULL DEFAULT TRUE,
            confidence      FLOAT DEFAULT 0.0,
            health_score    FLOAT DEFAULT 0.0,
            spans_json      JSONB DEFAULT '[]'::jsonb,
            events_json     JSONB DEFAULT '[]'::jsonb,
            metadata_json   JSONB DEFAULT '{}'::jsonb,
            user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at      TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_xray_traces_created_at ON xray_traces(created_at DESC);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_xray_traces_user_id ON xray_traces(user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_xray_traces_success ON xray_traces(success);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_xray_traces_strategy ON xray_traces(strategy);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_xray_traces_provider ON xray_traces(provider);")

    op.execute("ALTER TABLE xray_traces ENABLE ROW LEVEL SECURITY;")

    op.execute("""
        CREATE OR REPLACE FUNCTION cleanup_old_xray_traces()
        RETURNS void AS $$
        BEGIN
            DELETE FROM xray_traces WHERE created_at < NOW() - INTERVAL '90 days';
        END;
        $$ LANGUAGE plpgsql;
    """)

    # --- 018_memory_persistence.sql ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS persona_state (
            id TEXT PRIMARY KEY DEFAULT 'system',
            data JSONB NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS roots_knowledge (
            id TEXT PRIMARY KEY,
            text TEXT NOT NULL,
            category TEXT DEFAULT 'philosophy',
            priority INTEGER DEFAULT 50,
            immutable BOOLEAN DEFAULT TRUE,
            source TEXT DEFAULT 'system',
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS emotion_state (
            id TEXT PRIMARY KEY DEFAULT 'system',
            data JSONB NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    op.execute("ALTER TABLE persona_state ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE roots_knowledge ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE emotion_state ENABLE ROW LEVEL SECURITY;")

    # --- 019_episodic_semantic_postgres.sql ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS episodes (
            id TEXT PRIMARY KEY,
            timestamp TIMESTAMPTZ NOT NULL,
            user_id TEXT,
            situation TEXT DEFAULT '',
            participants JSONB DEFAULT '[]',
            location TEXT DEFAULT '',
            user_message TEXT NOT NULL,
            ai_response TEXT,
            intent TEXT DEFAULT 'unknown',
            topic TEXT DEFAULT 'общее',
            emotion_before JSONB DEFAULT '{}',
            emotion_after JSONB DEFAULT '{}',
            emotion_impact REAL DEFAULT 0.0,
            entities JSONB DEFAULT '[]',
            concepts JSONB DEFAULT '[]',
            keywords JSONB DEFAULT '[]',
            related_episodes JSONB DEFAULT '[]',
            parent_episode TEXT,
            continuation_of TEXT,
            significance REAL DEFAULT 0.5,
            access_count INTEGER DEFAULT 0,
            last_accessed TIMESTAMPTZ,
            duration_seconds REAL DEFAULT 0.0,
            success BOOLEAN DEFAULT TRUE,
            feedback TEXT
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_episodes_timestamp ON episodes(timestamp DESC);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_episodes_topic ON episodes(topic);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_episodes_significance ON episodes(significance DESC);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_episodes_user_id ON episodes(user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_episodes_intent ON episodes(intent);")

    op.execute("""
        CREATE TABLE IF NOT EXISTS episode_relations (
            id BIGSERIAL PRIMARY KEY,
            episode_id TEXT NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
            related_id TEXT NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
            relation_type TEXT DEFAULT 'related',
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_episode_relations_episode_id ON episode_relations(episode_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_episode_relations_related_id ON episode_relations(related_id);")

    op.execute("""
        CREATE TABLE IF NOT EXISTS semantic_knowledge (
            id TEXT PRIMARY KEY,
            knowledge_type TEXT NOT NULL,
            content TEXT NOT NULL,
            summary TEXT DEFAULT '',
            procedure_steps JSONB DEFAULT '[]',
            triggers JSONB DEFAULT '[]',
            success_rate REAL DEFAULT 0.5,
            related_concepts JSONB DEFAULT '[]',
            examples JSONB DEFAULT '[]',
            parent_knowledge TEXT,
            derived_from JSONB DEFAULT '[]',
            confidence REAL DEFAULT 0.5,
            source TEXT DEFAULT 'unknown',
            created_at TIMESTAMPTZ NOT NULL,
            last_accessed TIMESTAMPTZ,
            access_count INTEGER DEFAULT 0,
            last_modified TIMESTAMPTZ,
            tags JSONB DEFAULT '[]',
            domain TEXT DEFAULT 'general'
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_semantic_type ON semantic_knowledge(knowledge_type);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_semantic_domain ON semantic_knowledge(domain);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_semantic_confidence ON semantic_knowledge(confidence DESC);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_semantic_created ON semantic_knowledge(created_at DESC);")

    op.execute("""
        CREATE TABLE IF NOT EXISTS procedure_applications (
            id BIGSERIAL PRIMARY KEY,
            procedure_id TEXT NOT NULL REFERENCES semantic_knowledge(id) ON DELETE CASCADE,
            context TEXT NOT NULL,
            success BOOLEAN DEFAULT TRUE,
            applied_at TIMESTAMPTZ DEFAULT NOW(),
            feedback TEXT
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_procedure_applications_procedure_id ON procedure_applications(procedure_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_procedure_applications_applied_at ON procedure_applications(applied_at);")

    op.execute("ALTER TABLE episodes ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE episode_relations ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE semantic_knowledge ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE procedure_applications ENABLE ROW LEVEL SECURITY;")

    # --- 020_experiences_postgres.sql ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS experiences (
            id BIGSERIAL PRIMARY KEY,
            dialog_id TEXT NOT NULL,
            user_message TEXT NOT NULL,
            ai_response TEXT,
            interaction_type TEXT NOT NULL,
            signals JSONB DEFAULT '{}',
            significance REAL DEFAULT 0.0,
            expectation TEXT DEFAULT '',
            reality TEXT DEFAULT '',
            delta TEXT DEFAULT '',
            lessons JSONB DEFAULT '[]',
            strategy_success REAL DEFAULT 0.0,
            impulse_before JSONB DEFAULT '{}',
            emotion_before JSONB DEFAULT '{}',
            persona_before JSONB DEFAULT '{}',
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_experiences_dialog_id ON experiences(dialog_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_experiences_interaction_type ON experiences(interaction_type);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_experiences_significance ON experiences(significance DESC);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_experiences_created_at ON experiences(created_at DESC);")
    op.execute("ALTER TABLE experiences ENABLE ROW LEVEL SECURITY;")

    # --- 021_user_personas_postgres.sql ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_personas (
            user_id TEXT PRIMARY KEY,
            data JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_user_personas_updated ON user_personas(updated_at DESC);")
    op.execute("ALTER TABLE user_personas ENABLE ROW LEVEL SECURITY;")

    # --- 022_document_chunks.sql ---
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.execute("""
        CREATE TABLE IF NOT EXISTS document_chunks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            embedding vector(1536),
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id ON document_chunks(document_id);")

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE indexname = 'idx_document_chunks_embedding'
            ) THEN
                CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding ON document_chunks
                    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
            END IF;
        END $$;
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_document_chunks_content_gin ON document_chunks
            USING gin (to_tsvector('russian', content));
    """)
    op.execute("ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;")

    # --- 017_documents_trash.sql ---
    op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;")
    op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;")
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_documents_is_deleted
            ON documents(is_deleted) WHERE is_deleted = TRUE;
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_documents_active
            ON documents(user_id, is_deleted, created_at DESC) WHERE is_deleted = FALSE;
    """)

    # --- 016_enable_rls_memory_tables.sql ---
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Пользователи видят свои эпизоды' AND tablename='episodes') THEN
                CREATE POLICY "Пользователи видят свои эпизоды" ON episodes FOR SELECT
                    USING (user_id = auth.uid()::text);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Сервис может вставлять эпизоды' AND tablename='episodes') THEN
                CREATE POLICY "Сервис может вставлять эпизоды" ON episodes FOR INSERT
                    WITH CHECK (true);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Сервис может обновлять эпизоды' AND tablename='episodes') THEN
                CREATE POLICY "Сервис может обновлять эпизоды" ON episodes FOR UPDATE
                    USING (true);
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Пользователи видят связи своих эпизодов' AND tablename='episode_relations') THEN
                CREATE POLICY "Пользователи видят связи своих эпизодов" ON episode_relations FOR SELECT
                    USING (EXISTS (SELECT 1 FROM episodes WHERE episodes.id = episode_relations.episode_id AND episodes.user_id = auth.uid()::text));
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Сервис может вставлять связи эпизодов' AND tablename='episode_relations') THEN
                CREATE POLICY "Сервис может вставлять связи эпизодов" ON episode_relations FOR INSERT
                    WITH CHECK (true);
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Все пользователи читают знания' AND tablename='semantic_knowledge') THEN
                CREATE POLICY "Все пользователи читают знания" ON semantic_knowledge FOR SELECT USING (true);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Сервис может вставлять знания' AND tablename='semantic_knowledge') THEN
                CREATE POLICY "Сервис может вставлять знания" ON semantic_knowledge FOR INSERT WITH CHECK (true);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Сервис может обновлять знания' AND tablename='semantic_knowledge') THEN
                CREATE POLICY "Сервис может обновлять знания" ON semantic_knowledge FOR UPDATE USING (true);
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Все пользователи читают применения процедур' AND tablename='procedure_applications') THEN
                CREATE POLICY "Все пользователи читают применения процедур" ON procedure_applications FOR SELECT USING (true);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Сервис может вставлять применения процедур' AND tablename='procedure_applications') THEN
                CREATE POLICY "Сервис может вставлять применения процедур" ON procedure_applications FOR INSERT WITH CHECK (true);
            END IF;
        END $$;
    """)

    # --- Views ---
    op.execute("""
        CREATE OR REPLACE VIEW user_stats AS
        SELECT
            u.id, u.email,
            COUNT(DISTINCT s.id) as total_sessions,
            COUNT(DISTINCT m.id) as total_messages,
            COUNT(DISTINCT k.id) as total_keys,
            MAX(s.last_message_at) as last_activity
        FROM users u
        LEFT JOIN chat_sessions s ON u.id = s.user_id
        LEFT JOIN chat_messages m ON s.id = m.session_id
        LEFT JOIN user_api_keys k ON u.id = k.user_id
        GROUP BY u.id, u.email;
    """)

    op.execute("""
        CREATE OR REPLACE VIEW dialog_stats AS
        SELECT
            d.user_id,
            COUNT(DISTINCT d.id) as total_dialogs,
            COUNT(DISTINCT CASE WHEN d.is_favorite THEN d.id END) as favorite_dialogs,
            COUNT(DISTINCT m.id) as total_messages,
            MAX(d.last_message_at) as last_activity
        FROM dialogs d
        LEFT JOIN messages m ON d.id = m.dialog_id
        GROUP BY d.user_id;
    """)

    # --- RLS policies for user_api_keys, chat_sessions, chat_messages ---
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Users can view own keys' AND tablename='user_api_keys') THEN
                CREATE POLICY "Users can view own keys" ON user_api_keys FOR SELECT
                    USING (auth.uid()::text = user_id::text);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Users can insert own keys' AND tablename='user_api_keys') THEN
                CREATE POLICY "Users can insert own keys" ON user_api_keys FOR INSERT
                    WITH CHECK (auth.uid()::text = user_id::text);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Users can update own keys' AND tablename='user_api_keys') THEN
                CREATE POLICY "Users can update own keys" ON user_api_keys FOR UPDATE
                    USING (auth.uid()::text = user_id::text);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Users can delete own keys' AND tablename='user_api_keys') THEN
                CREATE POLICY "Users can delete own keys" ON user_api_keys FOR DELETE
                    USING (auth.uid()::text = user_id::text);
            END IF;
        END $$;
    """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Users can view own sessions' AND tablename='chat_sessions') THEN
                CREATE POLICY "Users can view own sessions" ON chat_sessions FOR SELECT
                    USING (auth.uid() = user_id);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Users can insert own sessions' AND tablename='chat_sessions') THEN
                CREATE POLICY "Users can insert own sessions" ON chat_sessions FOR INSERT
                    WITH CHECK (auth.uid() = user_id);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Users can update own sessions' AND tablename='chat_sessions') THEN
                CREATE POLICY "Users can update own sessions" ON chat_sessions FOR UPDATE
                    USING (auth.uid() = user_id);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Users can delete own sessions' AND tablename='chat_sessions') THEN
                CREATE POLICY "Users can delete own sessions" ON chat_sessions FOR DELETE
                    USING (auth.uid() = user_id);
            END IF;
        END $$;
    """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Users can view own messages' AND tablename='chat_messages') THEN
                CREATE POLICY "Users can view own messages" ON chat_messages FOR SELECT
                    USING (session_id IN (SELECT id FROM chat_sessions WHERE user_id = auth.uid()));
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Users can insert own messages' AND tablename='chat_messages') THEN
                CREATE POLICY "Users can insert own messages" ON chat_messages FOR INSERT
                    WITH CHECK (session_id IN (SELECT id FROM chat_sessions WHERE user_id = auth.uid()));
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Users can delete own messages' AND tablename='chat_messages') THEN
                CREATE POLICY "Users can delete own messages" ON chat_messages FOR DELETE
                    USING (session_id IN (SELECT id FROM chat_sessions WHERE user_id = auth.uid()));
            END IF;
        END $$;
    """)

    # --- RLS for user_settings, dialogs, messages, documents, document_collections ---
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Users can view own settings' AND tablename='user_settings') THEN
                CREATE POLICY "Users can view own settings" ON user_settings FOR SELECT
                    USING (auth.uid() = user_id);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Users can insert own settings' AND tablename='user_settings') THEN
                CREATE POLICY "Users can insert own settings" ON user_settings FOR INSERT
                    WITH CHECK (auth.uid() = user_id);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Users can update own settings' AND tablename='user_settings') THEN
                CREATE POLICY "Users can update own settings" ON user_settings FOR UPDATE
                    USING (auth.uid() = user_id);
            END IF;
        END $$;
    """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Users can view own dialogs' AND tablename='dialogs') THEN
                CREATE POLICY "Users can view own dialogs" ON dialogs FOR SELECT
                    USING (auth.uid() = user_id);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Users can insert own dialogs' AND tablename='dialogs') THEN
                CREATE POLICY "Users can insert own dialogs" ON dialogs FOR INSERT
                    WITH CHECK (auth.uid() = user_id);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Users can update own dialogs' AND tablename='dialogs') THEN
                CREATE POLICY "Users can update own dialogs" ON dialogs FOR UPDATE
                    USING (auth.uid() = user_id);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Users can delete own dialogs' AND tablename='dialogs') THEN
                CREATE POLICY "Users can delete own dialogs" ON dialogs FOR DELETE
                    USING (auth.uid() = user_id);
            END IF;
        END $$;
    """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Users can view own messages' AND tablename='messages') THEN
                CREATE POLICY "Users can view own messages" ON messages FOR SELECT
                    USING (dialog_id IN (SELECT id FROM dialogs WHERE user_id = auth.uid()));
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Users can insert own messages' AND tablename='messages') THEN
                CREATE POLICY "Users can insert own messages" ON messages FOR INSERT
                    WITH CHECK (dialog_id IN (SELECT id FROM dialogs WHERE user_id = auth.uid()));
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Users can delete own messages' AND tablename='messages') THEN
                CREATE POLICY "Users can delete own messages" ON messages FOR DELETE
                    USING (dialog_id IN (SELECT id FROM dialogs WHERE user_id = auth.uid()));
            END IF;
        END $$;
    """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Users can view own documents' AND tablename='documents') THEN
                CREATE POLICY "Users can view own documents" ON documents FOR SELECT
                    USING (auth.uid()::text = user_id::text);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Users can insert own documents' AND tablename='documents') THEN
                CREATE POLICY "Users can insert own documents" ON documents FOR INSERT
                    WITH CHECK (auth.uid()::text = user_id::text);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Users can update own documents' AND tablename='documents') THEN
                CREATE POLICY "Users can update own documents" ON documents FOR UPDATE
                    USING (auth.uid()::text = user_id::text);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Users can delete own documents' AND tablename='documents') THEN
                CREATE POLICY "Users can delete own documents" ON documents FOR DELETE
                    USING (auth.uid()::text = user_id::text);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Users can soft-delete own documents' AND tablename='documents') THEN
                CREATE POLICY "Users can soft-delete own documents" ON documents FOR UPDATE
                    USING (auth.uid()::text = user_id::text);
            END IF;
        END $$;
    """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Users can view own collections' AND tablename='document_collections') THEN
                CREATE POLICY "Users can view own collections" ON document_collections FOR SELECT
                    USING (auth.uid()::text = user_id::text);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Users can insert own collections' AND tablename='document_collections') THEN
                CREATE POLICY "Users can insert own collections" ON document_collections FOR INSERT
                    WITH CHECK (auth.uid()::text = user_id::text);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Users can update own collections' AND tablename='document_collections') THEN
                CREATE POLICY "Users can update own collections" ON document_collections FOR UPDATE
                    USING (auth.uid()::text = user_id::text);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Users can delete own collections' AND tablename='document_collections') THEN
                CREATE POLICY "Users can delete own collections" ON document_collections FOR DELETE
                    USING (auth.uid()::text = user_id::text);
            END IF;
        END $$;
    """)

    # --- RLS for xray_traces ---
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Пользователи видят свои трейсы' AND tablename='xray_traces') THEN
                CREATE POLICY "Пользователи видят свои трейсы" ON xray_traces FOR SELECT
                    USING (user_id = auth.uid());
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Сервис может вставлять трейсы' AND tablename='xray_traces') THEN
                CREATE POLICY "Сервис может вставлять трейсы" ON xray_traces FOR INSERT
                    WITH CHECK (true);
            END IF;
        END $$;
    """)

    # --- RLS for service_role tables (018-021) ---
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Service role has full access to persona_state' AND tablename='persona_state') THEN
                CREATE POLICY "Service role has full access to persona_state" ON persona_state TO service_role
                    USING (true) WITH CHECK (true);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Service role has full access to roots_knowledge' AND tablename='roots_knowledge') THEN
                CREATE POLICY "Service role has full access to roots_knowledge" ON roots_knowledge TO service_role
                    USING (true) WITH CHECK (true);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Service role has full access to emotion_state' AND tablename='emotion_state') THEN
                CREATE POLICY "Service role has full access to emotion_state" ON emotion_state TO service_role
                    USING (true) WITH CHECK (true);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Service role full access experiences' AND tablename='experiences') THEN
                CREATE POLICY "Service role full access experiences" ON experiences TO service_role
                    USING (true) WITH CHECK (true);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Service role full access user_personas' AND tablename='user_personas') THEN
                CREATE POLICY "Service role full access user_personas" ON user_personas TO service_role
                    USING (true) WITH CHECK (true);
            END IF;
        END $$;
    """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Anon can read persona_state' AND tablename='persona_state') THEN
                CREATE POLICY "Anon can read persona_state" ON persona_state FOR SELECT TO anon USING (true);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Anon can read roots_knowledge' AND tablename='roots_knowledge') THEN
                CREATE POLICY "Anon can read roots_knowledge" ON roots_knowledge FOR SELECT TO anon USING (true);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Anon can read emotion_state' AND tablename='emotion_state') THEN
                CREATE POLICY "Anon can read emotion_state" ON emotion_state FOR SELECT TO anon USING (true);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Anon read experiences' AND tablename='experiences') THEN
                CREATE POLICY "Anon read experiences" ON experiences FOR SELECT TO anon USING (true);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Anon read user_personas' AND tablename='user_personas') THEN
                CREATE POLICY "Anon read user_personas" ON user_personas FOR SELECT TO anon USING (true);
            END IF;
        END $$;
    """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Service role full access episodes' AND tablename='episodes') THEN
                CREATE POLICY "Service role full access episodes" ON episodes TO service_role USING (true) WITH CHECK (true);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Service role full access episode_relations' AND tablename='episode_relations') THEN
                CREATE POLICY "Service role full access episode_relations" ON episode_relations TO service_role USING (true) WITH CHECK (true);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Service role full access semantic_knowledge' AND tablename='semantic_knowledge') THEN
                CREATE POLICY "Service role full access semantic_knowledge" ON semantic_knowledge TO service_role USING (true) WITH CHECK (true);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Service role full access procedure_applications' AND tablename='procedure_applications') THEN
                CREATE POLICY "Service role full access procedure_applications" ON procedure_applications TO service_role USING (true) WITH CHECK (true);
            END IF;
        END $$;
    """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Anon read episodes' AND tablename='episodes') THEN
                CREATE POLICY "Anon read episodes" ON episodes FOR SELECT TO anon USING (true);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Anon read episode_relations' AND tablename='episode_relations') THEN
                CREATE POLICY "Anon read episode_relations" ON episode_relations FOR SELECT TO anon USING (true);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Anon read semantic_knowledge' AND tablename='semantic_knowledge') THEN
                CREATE POLICY "Anon read semantic_knowledge" ON semantic_knowledge FOR SELECT TO anon USING (true);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Anon read procedure_applications' AND tablename='procedure_applications') THEN
                CREATE POLICY "Anon read procedure_applications" ON procedure_applications FOR SELECT TO anon USING (true);
            END IF;
        END $$;
    """)

    # --- RLS for document_chunks ---
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Users can view own document chunks' AND tablename='document_chunks') THEN
                CREATE POLICY "Users can view own document chunks" ON document_chunks FOR SELECT
                    USING (EXISTS (SELECT 1 FROM documents WHERE documents.id = document_chunks.document_id AND documents.user_id::text = auth.uid()::text));
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Users can insert own document chunks' AND tablename='document_chunks') THEN
                CREATE POLICY "Users can insert own document chunks" ON document_chunks FOR INSERT
                    WITH CHECK (EXISTS (SELECT 1 FROM documents WHERE documents.id = document_chunks.document_id AND documents.user_id::text = auth.uid()::text));
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='Users can delete own document chunks' AND tablename='document_chunks') THEN
                CREATE POLICY "Users can delete own document chunks" ON document_chunks FOR DELETE
                    USING (EXISTS (SELECT 1 FROM documents WHERE documents.id = document_chunks.document_id AND documents.user_id::text = auth.uid()::text));
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS dialog_stats;")
    op.execute("DROP VIEW IF EXISTS user_stats;")

    op.execute("DROP TRIGGER IF EXISTS update_dialog_stats_after_delete ON messages;")
    op.execute("DROP TRIGGER IF EXISTS update_dialog_stats_after_insert ON messages;")
    op.execute("DROP FUNCTION IF EXISTS update_dialog_stats();")
    op.execute("DROP TRIGGER IF EXISTS on_user_created ON users;")
    op.execute("DROP FUNCTION IF EXISTS public.create_user_settings();")
    op.execute("DROP FUNCTION IF EXISTS public.check_tables_exist();")
    op.execute("DROP FUNCTION IF EXISTS cleanup_old_xray_traces();")

    op.execute("DROP TRIGGER IF EXISTS update_users_updated_at ON users;")
    op.execute("DROP TRIGGER IF EXISTS update_user_api_keys_updated_at ON user_api_keys;")
    op.execute("DROP TRIGGER IF EXISTS update_chat_sessions_updated_at ON chat_sessions;")
    op.execute("DROP TRIGGER IF EXISTS update_user_settings_updated_at ON user_settings;")
    op.execute("DROP TRIGGER IF EXISTS update_dialogs_updated_at ON dialogs;")
    op.execute("DROP TRIGGER IF EXISTS update_documents_updated_at ON documents;")
    op.execute("DROP TRIGGER IF EXISTS update_document_collections_updated_at ON document_collections;")

    op.execute("DROP TABLE IF EXISTS document_chunks CASCADE;")
    op.execute("DROP TABLE IF EXISTS procedure_applications CASCADE;")
    op.execute("DROP TABLE IF EXISTS episode_relations CASCADE;")
    op.execute("DROP TABLE IF EXISTS episodes CASCADE;")
    op.execute("DROP TABLE IF EXISTS semantic_knowledge CASCADE;")
    op.execute("DROP TABLE IF EXISTS experiences CASCADE;")
    op.execute("DROP TABLE IF EXISTS user_personas CASCADE;")
    op.execute("DROP TABLE IF EXISTS persona_state CASCADE;")
    op.execute("DROP TABLE IF EXISTS roots_knowledge CASCADE;")
    op.execute("DROP TABLE IF EXISTS emotion_state CASCADE;")
    op.execute("DROP TABLE IF EXISTS xray_traces CASCADE;")
    op.execute("DROP TABLE IF EXISTS document_collections CASCADE;")
    op.execute("DROP TABLE IF EXISTS documents CASCADE;")
    op.execute("DROP TABLE IF EXISTS messages CASCADE;")
    op.execute("DROP TABLE IF EXISTS dialogs CASCADE;")
    op.execute("DROP TABLE IF EXISTS user_settings CASCADE;")
    op.execute("DROP TABLE IF EXISTS chat_messages CASCADE;")
    op.execute("DROP TABLE IF EXISTS chat_sessions CASCADE;")
    op.execute("DROP TABLE IF EXISTS user_api_keys CASCADE;")
    op.execute("DROP TABLE IF EXISTS provider_configs CASCADE;")
    op.execute("DROP TABLE IF EXISTS users CASCADE;")

    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")
