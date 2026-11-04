import datetime as dt
import hashlib
import http.client
import json
import threading
import types
import unittest
from unittest.mock import patch
import server

class MailActionsTest(unittest.TestCase):
    def test_authenticated_same_origin_action_and_evidence_boundary(self):
        auth=server.PasswordAuth(b'test',b'x'*32,b'y'*32,b'z'*32)
        web=server.DashboardServer(('127.0.0.1',0),server.Handler)
        web.auth=auth;web.public_origin='http://127.0.0.1:'+str(web.server_port)
        threading.Thread(target=web.serve_forever,daemon=True).start()
        self.addCleanup(web.server_close);self.addCleanup(web.shutdown)
        body=json.dumps({'case_id':'a'*32,'action':'resolved','request_id':'b'*32,'expected':None,'remind_on':None})
        def request(cookie=True,origin=True,path='/api/mail-secretary/action',payload=None,**extra):
            connection=http.client.HTTPConnection('127.0.0.1',web.server_port,timeout=3)
            headers={'Content-Type':'application/json',**extra}
            if cookie:headers['Cookie']=auth.cookie().split(';')[0]
            if origin:headers['Origin']=web.public_origin if origin is True else origin
            connection.request('POST',path,body if payload is None else json.dumps(payload),headers)
            response=connection.getresponse();result=(response.status,response.read());connection.close();return result
        with patch.object(server,'mail_control',return_value={'available':True,'decisions':{}}) as broker:
            self.assertEqual(request(cookie=False)[0],401)
            self.assertEqual(request(origin=False)[0],403)
            self.assertEqual(request(origin='https://evil.example')[0],403)
            self.assertEqual(request(**{'Content-Type':'text/plain'})[0],415)
            self.assertEqual(request(cookie=False,path='/api/mail-secretary/history')[0],401)
            self.assertEqual(request(origin='https://evil.example',path='/api/mail-secretary/history')[0],403)
            broker.assert_not_called()
            self.assertEqual(request()[0],200)
            self.assertEqual(broker.call_args.args[0]['operation'],'action')
            self.assertEqual(request(path='/api/mail-secretary/history',payload={'case_id':'a'*32})[0],200)
            self.assertEqual(broker.call_args.args[0],{'operation':'history','case_id':'a'*32})
            broker.return_value={'error':'decision_conflict'}
            self.assertEqual(request()[0],409)
        with patch.object(server,'mail_control',side_effect=OSError('PRIVATE_ERROR')):
            code,data=request();self.assertEqual(code,503);self.assertNotIn(b'PRIVATE_ERROR',data)
