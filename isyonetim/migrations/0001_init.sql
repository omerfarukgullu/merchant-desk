-- 0001_init.sql
-- Iş yönetim sistemi ilk şema: proje/aşama/görev, toplantı/aksiyon, e-ticaret modülleri.

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    goal TEXT,
    status TEXT NOT NULL DEFAULT 'planned'
        CHECK (status IN ('planned', 'in_progress', 'completed', 'on_hold')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS phases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'planned'
        CHECK (status IN ('planned', 'in_progress', 'completed', 'on_hold')),
    order_index INTEGER NOT NULL DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_phases_project ON phases (project_id);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
    phase_id INTEGER REFERENCES phases (id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'planned'
        CHECK (status IN ('planned', 'in_progress', 'completed', 'on_hold')),
    priority_bucket TEXT NOT NULL DEFAULT 'backlog'
        CHECK (priority_bucket IN ('today', 'this_week', 'backlog')),
    due_date DATE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks (project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_phase ON tasks (phase_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks (status);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks (priority_bucket);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks (due_date);

CREATE TABLE IF NOT EXISTS meetings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES projects (id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    meeting_type TEXT NOT NULL DEFAULT 'other'
        CHECK (meeting_type IN ('supplier', 'customer', 'accountant', 'internal', 'other')),
    meeting_date DATE NOT NULL,
    participants TEXT,
    agenda TEXT,
    decisions TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_meetings_project ON meetings (project_id);
CREATE INDEX IF NOT EXISTS idx_meetings_date ON meetings (meeting_date);

CREATE TABLE IF NOT EXISTS action_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id INTEGER NOT NULL REFERENCES meetings (id) ON DELETE CASCADE,
    task_id INTEGER REFERENCES tasks (id) ON DELETE SET NULL,
    description TEXT NOT NULL,
    owner TEXT NOT NULL,
    due_date DATE,
    status TEXT NOT NULL DEFAULT 'open'
        CHECK (status IN ('open', 'done', 'cancelled')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_action_items_meeting ON action_items (meeting_id);
CREATE INDEX IF NOT EXISTS idx_action_items_status ON action_items (status);
CREATE INDEX IF NOT EXISTS idx_action_items_due_date ON action_items (due_date);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    sku TEXT UNIQUE,
    category TEXT,
    cost_price REAL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    channel_type TEXT NOT NULL DEFAULT 'marketplace'
        CHECK (channel_type IN ('own_site', 'marketplace', 'social', 'other')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products (id) ON DELETE CASCADE,
    channel_id INTEGER NOT NULL REFERENCES channels (id) ON DELETE CASCADE,
    price REAL,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'inactive', 'out_of_stock')),
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (product_id, channel_id)
);
CREATE INDEX IF NOT EXISTS idx_listings_product ON listings (product_id);
CREATE INDEX IF NOT EXISTS idx_listings_channel ON listings (channel_id);

CREATE TABLE IF NOT EXISTS price_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products (id) ON DELETE CASCADE,
    channel_id INTEGER REFERENCES channels (id) ON DELETE SET NULL,
    source TEXT NOT NULL DEFAULT 'own'
        CHECK (source IN ('own', 'competitor')),
    competitor_name TEXT,
    price REAL NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    note TEXT,
    CHECK (
        (source = 'own' AND channel_id IS NOT NULL AND competitor_name IS NULL)
        OR (source = 'competitor' AND competitor_name IS NOT NULL)
    )
);
CREATE INDEX IF NOT EXISTS idx_price_records_product ON price_records (product_id);
CREATE INDEX IF NOT EXISTS idx_price_records_recorded_at ON price_records (recorded_at);

CREATE TABLE IF NOT EXISTS sale_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products (id) ON DELETE CASCADE,
    channel_id INTEGER NOT NULL REFERENCES channels (id) ON DELETE RESTRICT,
    sale_date DATE NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price REAL NOT NULL,
    unit_cost REAL,
    note TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_sale_records_product ON sale_records (product_id);
CREATE INDEX IF NOT EXISTS idx_sale_records_channel ON sale_records (channel_id);
CREATE INDEX IF NOT EXISTS idx_sale_records_date ON sale_records (sale_date);
