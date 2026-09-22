DO $$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'agent_readonly') THEN
      CREATE ROLE agent_readonly LOGIN PASSWORD 'agent_readonly_password';
   END IF;
END
$$;

GRANT CONNECT ON DATABASE agentic_rag TO agent_readonly;
GRANT USAGE ON SCHEMA public TO agent_readonly;
GRANT SELECT ON orders TO agent_readonly;
REVOKE ALL ON documents, chat_history, users FROM agent_readonly;
