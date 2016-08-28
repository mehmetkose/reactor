
import tornado.web


class BaseHandler(tornado.web.RequestHandler):

    def initialize(self):
        self.db = self.application.db
    
    def get_current_user(self):
        user = self.get_secure_cookie("user")
        if not user: return None
        return tornado.escape.xhtml_escape(user)

    def get_user_locale(self):
        #TODO : get user lang value from DB or browser heads and set like this.
        return tornado.locale.get("tr_TR")

    def write_json(self, obj):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.finish(json.dumps(obj))

    def generate_token(self):
        return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(32))

    @tornado.gen.coroutine
    def handle_query(self, query):
        result = {'success':True, 'data':None}
        if str(query['version']) == "1":

            if query['method'] == 'post' and query['key'] == 'new' and query['value']=='one':
                self.write('save one')
                raise tornado.gen.Return(None)
            
            elif query['method'] == 'list' and 'table' in query and query['key'] == "get" and query['value'] == "all":
                cursor = yield r.table(query['table']).run(self.db)
                items = yield self.iterate_cursor(cursor)
                result['count'] = len(items)
                result['data'] = items

            elif query['method'] == 'list' and 'table' in query and 'key' in query and 'value' in query:
                cursor = yield r.table(query['table']).filter(r.row[query['key']] == query['value']).run(self.db)
                items = yield self.iterate_cursor(cursor)
                result['count'] = len(items)
                result['data'] = items

            elif query['method'] == 'related' and 'table' in query and 'key' in query and 'value' in query:
                table_name = query['table']
                key = query['key']
                value = query['value']
                
                try:
                    raw_object = getattr(settings, 'raw_%s' % (table_name))
                except AttributeError as e:
                    result['success'] = False
                    result['message'] = 'relation not exists'
                    raise tornado.gen.Return(result)

                left_id = list(raw_object.keys())[0]
                left_name = "%ss" % list(raw_object.keys())[0].split('_id')[0]
                
                right_id = list(raw_object.keys())[1]
                right_name = "%ss" % list(raw_object.keys())[1].split('_id')[0]

                # cursor = yield r.table(query['table']).eq_join("user_id", r.table("users")).zip().eq_join(
                #     "store_id", r.table("stores")).zip().filter(r.row['user_id'] == '510ffc66-716c-41b5-aeb8-4fb7a44c9be0').run(self.db)
                cursor = yield r.table(table_name).eq_join(left_id, r.table(left_name)).zip().eq_join(
                    right_id, r.table(right_name)).zip().filter(r.row[key] == value).run(self.db)
                items = yield self.iterate_cursor(cursor)
                result['count'] = len(items)
                result['data'] = items
                result['success'] = True

            elif 'related_extend' in query['method'] and '_to_' in query['method'] and 'table' in query and 'key' in query and 'value' in query:
                related1 = query['method'].split('related_extend_')[1].split('_to_')[0]
                related2 = query['method'].split('related_extend_')[1].split('_to_')[1]
                
                query['method'] = 'related'
                query['key'] = 'user_email'
                result = yield self.handle_query(query)
                for data in result['data']:
                    for data_key in data.keys():
                        if '_id' in data_key:
                            related_id = data[data_key]
                            table_name = data_key.split('_id')[0]
                            if not table_name[-1] == "s":
                                table_name += "s"
                            result[table_name] = []
                            query['method'] = 'list'
                            query['table'] = table_name
                            query['key'] = 'id'
                            query['value'] = related_id
                            result = yield self.handle_query(query)
                            result[table_name] = result['data']
                
                if related1 in result:
                    for rel in result[related1]:
                        print("simdi idsi "+rel['id']+ " olan "+related2+'leri getirip sonuca ekliycem')
                        related1_plural = related1
                        if related1_plural[-1] == 's':
                            related1_plural = related1_plural[:-1]
                        result[related2] = []
                        query['method'] = 'list'
                        query['table'] = related2
                        query['key'] = '%s_id' % (related1_plural)
                        query['value'] = rel['id']
                        device_result = yield self.handle_query(query)
                        result[related2] = device_result['data']


            if query['method'] == 'save_device' and query['key'] == 'get' and query['value']=='token':
                token = self.generate_token()
                result['success'] = True
                result['token'] = "%s-t%s" % (token, str(int(time.time())))
                raise tornado.gen.Return(result)

            if query['method'] == 'save_device' and query['key'] == 'confirm' and 'value' in query:
                device = copy.deepcopy(settings.raw_devices)
                device['device_key'] = query['value']
                device['ip'] = self.request.remote_ip or None
                save_results = yield self.save_unique(
                    table= 'devices', 
                    check_dict= {'device_key':device['device_key']},
                    insert_dict= device
                )
                if save_results['inserted'] > 0:
                    result['success'] = True
                    result['message'] = "device recorded"                    
                else:
                    result['success'] = False
                    result['message'] = "device already exists"

                raise tornado.gen.Return(result)
            else:
                result['success'] = False
        else:
            result['success'] = False
            result['message'] = "error with api version"

        raise tornado.gen.Return(result)


    @tornado.gen.coroutine
    def iterate_cursor(self, cursor):
        items = []
        while (yield cursor.fetch_next()):
            item = yield cursor.next()
            items.append(item)
        raise tornado.gen.Return(items)

    @tornado.gen.coroutine
    def db_order(self, table, index='add_date', order_by='desc'):
        if order_by == "desc":
            direction = r.desc(index)
        else:
            direction = r.asc(index)
        cursor = yield r.table(table).order_by(index=direction).run(self.db)
        items = yield self.iterate_cursor(cursor)
        raise tornado.gen.Return(items)


    @tornado.gen.coroutine
    def db_filter(self, table, query):
        cursor = yield r.table(table).filter(query).run(self.db)
        items = yield self.iterate_cursor(cursor)
        raise tornado.gen.Return(items)


    @tornado.gen.coroutine
    def db_insert(self, table, insert_dict):
        results = yield r.table(table).insert(insert_dict).run(self.db)
        raise tornado.gen.Return(results)

    @tornado.gen.coroutine
    def save_unique(self, table, check_dict, insert_dict):
        # check_dict = {'user_id': stores_users["user_id"], 'store_id': stores_users["store_id"]}
        items = yield self.db_filter(table, check_dict)
        if len(items)==0:
            results = yield r.table(table).insert(insert_dict).run(self.db)
            raise tornado.gen.Return(results)
        raise tornado.gen.Return(False)

    @tornado.gen.coroutine
    def get_one(self, table, key, value):
        cursor = yield r.table(table).filter(r.row[key] == value).limit(1).run(self.db)
        while (yield cursor.fetch_next()):
            item = yield cursor.next()
            raise tornado.gen.Return(item)
        raise tornado.gen.Return(False)

    @tornado.gen.coroutine
    def update_one(self, table, id, update_dict):
        results = yield r.table(table).get(id).update(update_dict).run(self.db)
        raise tornado.gen.Return(results)

    @tornado.gen.coroutine
    def db_m2m_filter(self, table1, table2, key, value):
        raise tornado.gen.Return("hello")