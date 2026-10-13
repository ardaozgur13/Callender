"""
Supabase pooler'a uygun test çalıştırıcısı.

Pooler (Transaction mode) testler bittikten sonra test veritabanına bir bağlantıyı açık tutar;
Django'nun düz `DROP DATABASE` komutu bu yüzden "is being accessed by other users" hatasıyla düşer.
PostgreSQL 13+ `DROP DATABASE ... WITH (FORCE)` bu bağlantıları kapatıp silebildiği için
test veritabanı oluşturma/silme adımlarında onu kullanıyoruz.
"""
from django.db import connections
from django.test.runner import DiscoverRunner


def _force_drop(creation):
    def _destroy_test_db(test_database_name, verbosity):
        with creation._nodb_cursor() as cursor:
            cursor.execute(
                "DROP DATABASE IF EXISTS %s WITH (FORCE)" % creation.connection.ops.quote_name(test_database_name)
            )

    return _destroy_test_db


class PoolerSafeTestRunner(DiscoverRunner):
    def setup_databases(self, **kwargs):
        for alias in connections:
            connection = connections[alias]
            if connection.vendor == "postgresql":
                connection.creation._destroy_test_db = _force_drop(connection.creation)
        return super().setup_databases(**kwargs)
