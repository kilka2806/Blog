import sqlite3

connection = sqlite3.connect('sqlite.db')
cursor = connection.cursor()
cursor.execute('''create table post_like (
id integer primary key autoincrement,
post_id integer not null ,
user_id integer not null )''')

connection.commit()
cursor.close()
connection.close()