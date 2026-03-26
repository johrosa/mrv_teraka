import psycopg2
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    dbname="teraka",
    user="postgres",
    password="ad,in"
)
with conn, conn.cursor() as cur:
    cur.execute("""
                SELECT table_name, column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                ORDER BY table_name, ordinal_position;
                """)
    rows = cur.fetchall()
with open("structure.txt", "w", encoding="utf-8") as f:
    current = None
    for table, col, dtype, nullable in rows:
        if table != current:
            current = table
            f.write(f"\n[{table}]\n")
        f.write(f"  - {col}: {dtype} (nullable={nullable})\n")
conn.close()