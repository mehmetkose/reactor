#!/usr/bin/env python
#-*- coding:utf-8 -*-

import logging, os.path, time, copy, json, random, string
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.locale
import tornado.websocket
import tornado.gen
import tornado.escape

from tornado.options import define, options

import settings

import rethinkdb as r

from handlers.preact import PreactHandler

define("port", default=settings.port, help="run on the given port", type=int)
define("debug", default=settings.debug, help="run in debug mode", type=bool)

class Application(tornado.web.Application):

    def __init__(self, db):
        self.db = db
        base_dir = os.path.dirname(__file__)
        app_settings = {
            "login_url": "/",
            "debug": options.debug,
            "cookie_secret": settings.cookie_secret,
            "static_path": os.path.join(base_dir, "static/%s" % (settings.theme)),
            "template_path": os.path.join(base_dir, "templates/%s" % (settings.theme)),
        }
        tornado.web.Application.__init__(self, [
            tornado.web.url(r".*", PreactHandler, name="catch"),
        ], **app_settings)


@tornado.gen.coroutine
def main():
    tornado.options.parse_command_line()
    # setup localization
    translationsPath = os.path.join(os.path.dirname(__file__), "translations")
    tornado.locale.load_translations(translationsPath)
    tornado.locale.set_default_locale("tr_TR")
    # set connection
    r.set_loop_type("tornado")
    db = yield r.connect(settings.db_ip, db=settings.db_name)
    # setup server
    http_server = tornado.httpserver.HTTPServer(Application(db))
    http_server.listen(options.port)
    logging.info("application running on http://localhost:%s" % (options.port))

if __name__ == "__main__":
    tornado.ioloop.IOLoop.current().run_sync(main)
    tornado.ioloop.IOLoop.current().start()
