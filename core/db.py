"""
Supabase güvenliği: Supabase, `public` şemasındaki tabloları kendi REST API'si (PostgREST)
üzerinden de açar. Callender bu API'yi kullanmaz; Django tablo sahibi `postgres` rolüyle
bağlanır ve RLS'den etkilenmez. Bu yüzden her tabloda RLS açılır ve hiç kural (policy)
tanımlanmaz; böylece anon/authenticated rolleri API üzerinden hiçbir satıra erişemez.
"""

ENABLE_RLS_SQL = """
DO $$
DECLARE t record;
BEGIN
    FOR t IN
        SELECT c.relname
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind = 'r' AND NOT c.relrowsecurity
    LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t.relname);
    END LOOP;
END $$;
"""


def enable_rls_on_public_tables(using="default", **kwargs):
    """post_migrate sinyali: RLS'si kapalı tüm public tablolarda RLS'yi açar."""
    from django.db import connections

    connection = connections[using]
    if connection.vendor != "postgresql":
        return
    with connection.cursor() as cursor:
        cursor.execute(ENABLE_RLS_SQL)
