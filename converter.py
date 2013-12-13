#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys, time
import os
import subprocess
from datetime import datetime
import web
import re

from daemon import Daemon
import model

from DocumentConverter import DocumentConverter
from DocumentConverter import DocumentConversionException
from com.sun.star.task import ErrorCodeIOException
import threading
 
urls = ('/upload', 'Upload',
        '/get/(\d*)/', 'GetImage',
        '/getinfo/(\d*)/', 'GetInfo',
        '/isready/(\d*)/','IsImageReady')
        
class GetInfo:
    def GET(self,id):                
        return model.get_task(id).tittle
        
        
class GetImage:
    def GET(self,id):                
        return model.get_task_content(id)
        
        
class IsImageReady:
    def GET(self,id):                
        return model.is_ready(id)['ready']
        
class Upload:
    def GET(self):
        return """<html><head></head><body>
<form method="POST" enctype="multipart/form-data" action="">
<input type="file" name="file" />
<br/>
<input type="submit" />
</form>
</body></html>"""

        
        
    def POST(self):       
        mydoc = web.input(file={})['file']       
        #записали файл
        f = open('/tmp/converterdir/'+mydoc.filename, 'w')            
        f.write(mydoc.value)        
        #зарегисрировали задачу
        n = model.new_task(mydoc.filename, 0,'/tmp/converterdir/'+mydoc.filename)        
        #вернули её номер
        return n;

class ConverterThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        if not os.path.exists('/tmp/converterdir'):
            os.makedirs('/tmp/converterdir')
        
        #flog = open('/tmp/converterdir/test.log', 'w')
        self.flog = open('/var/opt/converter/convertThread.log', 'w')
        #Вырубили все инстанцы ОО и запустили новый
        subprocess.call("killall -u 'root' -q soffice ", shell=True, stdout=self.flog)
        subprocess.Popen('/usr/bin/ooffice -accept="socket,host=localhost,port=8100;urp;StarOffice.ServiceManager" -norestore -nofirststartwizard -nologo -headless ', shell=True, stdout=self.flog)
        #Дождались пока он точно стартанёт
        time.sleep(5)
        model.init_db()        
        
    def run(self):
        while True:            
            doc = model.get_task_to_process()            
            if doc is None:
                time.sleep(1)
            else:
                try:
                    #log selected document
                    web.debug(doc)                   
                    #ensure that tmp direcory exist
                    if not os.path.exists('/tmp/converterdir'):
                        os.makedirs('/tmp/converterdir')
                    
                    #check if document need to been converted
                    interim_path = '/tmp/converterdir/test2.pdf'                    
                    if re.search(r"\.pdf$", doc.srcname, re.IGNORECASE | re.MULTILINE) is None:
                        converter = DocumentConverter()    
                        converter.convert(doc.srcname, interim_path)                        
                        #wait for converter closes
                        time.sleep(1)
                    else:
                        #call pdftk to atach original pdf to new pdf without signature
                        #subprocess.call("/opt/zimbra/bin/pdftk "+ doc.srcname +" cat '"+doc.srcname +"' output "+interim_path, shell=True, stdout=self.flog)
                        interim_path = doc.srcname
                        
                    web.debug(interim_path)
                    #call pdftk to atach original
                    subprocess.call("/opt/zimbra/bin/pdftk "+ interim_path +" attach_files '"+doc.srcname +"' output /tmp/converterdir/test3.pdf", shell=True, stdout=self.flog)
                    
                    #sign document with Private Key from key.properties
                    d = datetime.today()
                    unic_file_name = d.strftime('%m_%d_%H_%M_%S')
                    subprocess.call("java -jar /opt/zimbra/bin/signapp/signApp.jar /tmp/converterdir/test3.pdf /tmp/converterdir/"+unic_file_name+".pdf /opt/zimbra/bin/signapp/key.properties", shell=True, stdout=self.flog)
                    
                    #mark document as ready
                    model.update_task(doc.idtask, 10, '/tmp/converterdir/'+unic_file_name+'.pdf')
                    
                except DocumentConversionException, exception:
                    model.update_task(doc.idtask, -1)
                    web.debug(datetime.today().strftime('%y-%m-%d %H:%M:%S')+"ERROR! " + str(exception))                    
                except ErrorCodeIOException, exception:
                    model.update_task(doc.idtask, -1)
                    web.debug(datetime.today().strftime('%y-%m-%d %H:%M:%S')+"ERROR! ErrorCodeIOException %d" % exception.ErrCode )
                except Exception, exception:
                    model.update_task(doc.idtask, -1)
                    web.debug(datetime.today().strftime('%y-%m-%d %H:%M:%S') + " unexpected error! - " + str(exception))
                        ##st_out, st_in, st_error = Popen.popen(command)
        
class MyDaemon(Daemon):

    def run(self):
        sys.argv[1:] = ['8181']         
        task = ConverterThread()
        task.start()
        web.config.debug = False 
        app = web.application(urls, globals())         
        app.run()        
        while True:
            time.sleep(1)

if __name__ == "__main__":
    daemon = MyDaemon('/var/opt/converter/converter.pid','/dev/null','/var/opt/converter/converter.log','/var/opt/converter/converter.log')
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        else:
            print "Unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)
