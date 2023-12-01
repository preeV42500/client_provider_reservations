import sqlite3
conn = sqlite3.connect("reservations.db")

# cursor = conn.cursor()


provider_table_columns = [
"id INTEGER PRIMARY KEY",
"npi BIGINT UNSIGNED NOT NULL",
"firstname VARCHAR NOT NULL",
"lastname VARCHAR NOT NULL",
"available_on DATE NOT NULL",
]

create_provider_table_cmd = f"CREATE TABLE IF NOT EXISTS provider ({','.join(provider_table_columns)})"
conn.execute(create_provider_table_cmd)

appointment_table_columns = [
    "id INTEGER PRIMARY KEY",
    "start_time DATETIME NOT NULL",
    "date DATE NOT NULL",
    "provider_id INTEGER NOT NULL",
    "reserved_at DATETIME",
    "confirmed_at DATETIME",
    "FOREIGN KEY (provider_id) REFERENCES provider (id)",
]

create_appointment_table_cmd = f"CREATE TABLE IF NOT EXISTS appointment_slots ({','.join(appointment_table_columns)})"
conn.execute(create_appointment_table_cmd)