#!/usr/bin/env python

import copy
import rethinkdb as r

port = 9999
debug = True
cookie_secret = '___YOUR_CLIENT_SECRET___'

theme = "base"

db_ip = "127.0.0.1"
db_name = "reactor"

table_names = ['users','posts']

def setup_db(db_name, tables):
    connection = r.connect(host="127.0.0.1")
    try:
        r.db_create(db_name).run(connection)
        print('Database setup completed: %s' % (db_name))
    except r.RqlRuntimeError:
        print('Datbase already exists : %s' % (db_name))

    for table in tables:
        try:
            r.db(db_name).table_create(table, durability="hard").run(connection)
            print('Table created: %s' % (table))
        except:
            print('Table already exists : %s' % (table))

    try:r.db(db_name).table("users").index_create("add_date").run(connection)
    except:pass

    try:r.db(db_name).table("posts").index_create("post_slug").run(connection)
    except:pass

    connection.close()

setup_db(db_name=db_name, tables=table_names)

raw_posts = {"post_title" : None,"post_slug" : None,"post_body": None, "statistics":[]}
raw_users = {"user_email" : None,"user_slug" : None,"user_password": None,"user_password_hint": None}

