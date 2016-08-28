
from handlers.base import BaseHandler

class PreactHandler(BaseHandler):
    def get(self):
        self.write('Hello World')