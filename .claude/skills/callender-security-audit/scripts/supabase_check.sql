-- Callender: Supabase güvenlik kontrolü. Supabase panelinde SQL Editor'de çalıştır (sadece okuma).
-- Amaç: Django tabloları "public" şemasında. Supabase'in otomatik REST (Data API) uç noktası
-- bu şemayı varsayılan olarak yayınlar; RLS kapalıysa anon anahtarıyla veri okunup yazılabilir.

-- 1) RLS KAPALI tablolar (Django tablolarının hepsi burada görünür; ideal: ya Data API kapalı ya da hepsi rowsecurity = true)
select schemaname, tablename, rowsecurity
from pg_tables
where schemaname = 'public'
order by rowsecurity, tablename;

-- 2) anon / authenticated rollerinin tablo yetkileri (ideal: sonuç BOŞ)
select grantee, table_name, string_agg(privilege_type, ', ' order by privilege_type) as yetkiler
from information_schema.role_table_grants
where table_schema = 'public' and grantee in ('anon', 'authenticated')
group by grantee, table_name
order by table_name, grantee;

-- 3) Django'nun bağlandığı rolün RLS'i atlayıp atlamadığı (postgres rolü için rolbypassrls = true beklenir)
select rolname, rolbypassrls from pg_roles where rolname in ('postgres', 'anon', 'authenticated', 'service_role');

------------------------------------------------------------------------------------------
-- DÜZELTME (Aşağıdakini SADECE sonuçları gördükten ve onayladıktan sonra çalıştır):
--
-- 1. Önce en güçlü önlem: Supabase panelinde Project Settings > Data API > "Enable Data API" KAPALI.
--    (Uygulama Supabase'e sadece doğrudan Postgres bağlantısıyla gidiyor, REST API'ye ihtiyaç yok.)
-- 2. Ek katman (savunma derinliği): aşağıdaki blok. Sonra uygulamayı dene; Django 'postgres' rolüyle
--    bağlandığı için etkilenmemeli.
--
-- do $$ declare r record; begin
--   for r in select tablename from pg_tables where schemaname = 'public' loop
--     execute format('alter table public.%I enable row level security', r.tablename);
--   end loop;
-- end $$;
-- revoke all on all tables in schema public from anon, authenticated;
-- revoke all on all sequences in schema public from anon, authenticated;
-- alter default privileges for role postgres in schema public revoke all on tables from anon, authenticated;
-- alter default privileges for role postgres in schema public revoke all on sequences from anon, authenticated;
-- Not: Yeni tablo eklendikçe (her migration sonrası) 1. sorguyu tekrar çalıştır.
