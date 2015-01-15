#!/usr/bin/python

from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
from contextlib import closing
import socket

PORT_NUMBER = 8088

def call_socket(host, port, payload):
  try:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
      s.connect((host, port))
      s.sendall(payload)
      s.shutdown(socket.SHUT_WR)
      full_data = ''
      while 1:
        data = s.recv(1024)
        full_data += data
        if data == '':
           return full_data
  except socket.error as e:
    print e
    return ''

class handler(BaseHTTPRequestHandler):
  def do_GET(self):
    data = call_socket('localhost', 2181, 'stat')
    endpoint_up = 'version' in data

    if endpoint_up:
      self.send_response(200)
    else:
      self.send_response(500)
    self.send_header('Content-type','text/html')
    self.end_headers()
    # Send the html message
    if endpoint_up:
      self.wfile.write("endpoint up")
    else:
      self.wfile.write("endpoint down")
    return

try:
  #Create a web server and define the handler to manage the
  #incoming request
  server = HTTPServer(('', PORT_NUMBER), handler)
  print 'Started httpserver on port ' , PORT_NUMBER

  #Wait forever for incoming htto requests
  server.serve_forever()

except KeyboardInterrupt:
  print '^C received, shutting down the web server'
  server.socket.close()
