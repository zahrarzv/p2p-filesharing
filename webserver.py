import socket
import select
import argparse
import sys
import os
import re        # good for matching things!
import uuid      # unique ID stuff
import json
import tempfile  # unique ID stuff
import time      # for timeouts
import threading


#DBserverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
DBHost = sys.argv[3] #loon.cs.umanitoba.ca
DBPort = int(sys.argv[4]) #8226


     

def manage_client(clientSocket):
    try:
        
            htmlReq = clientSocket.recv(4096).decode("utf-8")
            #if not htmlReq:
              # break
            content_length = 0
            match = re.search(r"Content-Length: (\d+)", htmlReq)
            if match:
               content_length = int(match.group(1))

            header,body = htmlReq.split("\r\n\r\n", 1)
            body_bytes = body.encode("utf-8")
            if len(body_bytes) < content_length:
               remaining = content_length - len(body_bytes)
               while remaining > 0:
                  data = clientSocket.recv(min(4096, remaining))
                  if not data:
                     break
                  body_bytes += data
                  remaining -= len(data)
               body = body_bytes.decode("utf-8", errors="replace")
                  
            
            request_lines = header.split("\r\n")
            request_line = request_lines[0]
            #(request_line)
            method, path, _ = request_line.split(" ")


            
            if method == "GET" and path == "/api/refresh":
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as db:
                        db.connect((DBHost, DBPort))
                        # tell the peer‐server what you want:
                        pReq = json.dumps({"type": "RETURN_PEERSLIST"}) + "\n"
                        db.sendall(pReq.encode("utf-8"))
                        peers = recv_full_message(db)
                        
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as db:
                        db.connect((DBHost, DBPort))
                        fReq = json.dumps({"type": "RETURN_FMETADATA"}) + "\n"
                        db.sendall(fReq.encode("utf-8"))
                        files = recv_full_message(db)
                        



                        try:
                            peers_list = json.loads(peers)     
                            files_list = json.loads(files)
                        except json.JSONDecodeError:
                            peers_list = [] 
                            files_list = []
                     
        
                        if peers: 
                            response = json.dumps({"peers":peers_list,"files":files_list})
                            sLine = "HTTP/1.1 200 OK\r\n"
                            response = (f"{sLine}"
                            "Content-Type: application/json\r\n"
                            "Access-Control-Allow-Origin: *\r\n"
                            "Connection: keep-alive\r\n" 
                            "Content-Length: " + str(len(response)) + "\r\n"
                            "\r\n"
                           f"{response}")
                        else: 
                            sLine = "HTTP/1.1 400 Bad Request\r\n"
                            response = json.dumps({"status": "unsuccessful"})
                            response = (f"{sLine}"
                            "Content-Type: application/json\r\n"
                            "Access-Control-Allow-Origin: *\r\n"
                            "Connection: keep-alive\r\n" 
                            "Content-Length: " + str(len(response)) + "\r\n"
                            "\r\n"
                           f"{response}")

                    clientSocket.sendall(response.encode("utf-8"))
                    # try:
                    #     peers_dict = json.loads(raw)
                    # except json.JSONDecodeError:
                    #     print("Could not parse JSON from peer‑server:", repr(raw))
                    #     peers_dict = {}
                except Exception as e:
                    print("Exception in /api/refresh handler:", e)

            ####------------------ADDED METHOD FOR APPEAL TO GET SERVER TO WORK AND GET PARTIAL MARKS-----------------------------###
            ### as mentioned in the READme, this is my added method that serves the file on this path/ 
            elif method == "GET" and path == "/webpage.html":
                # Serve the static HTML file
                try:
                    with open("webpage.html", "r") as file:
                        html_content = file.read()
                        sLine = "HTTP/1.1 200 OK\r\n"
                    response = (
                       f"{sLine}"
                        "Content-Type: text/html\r\n"
                        "Content-Length: " + str(len(html_content)) + "\r\n"
                        "\r\n"
                        + html_content
                    )
                    clientSocket.sendall(response.encode("utf-8"))
                except FileNotFoundError:
                    sLine  = "HTTP/1.1 404 Not Found\r\n"
                    response = (
                        f"{sLine}"
                        "Content-Type: text/plain\r\n"
                        "\r\n"
                        "404 Not Found: no file founf."
                    )
            elif method == "GET" and path == "/favicon.ico":
                sLine =  "HTTP/1.1 404 Not Found\r\n"
                response = (
                    f"{sLine}"
                    "Content-Type: text/plain\r\n"
                    "\r\n"
                    "404 Not Found: not found."
                )
                clientSocket.sendall(response.encode("utf-8"))
         #--------------------------------------------------------------------------------------
          

               



                

 
    except Exception as e:
            print(e)
    except Exception as e:
        print("handler error:", e)
    finally:
          clientSocket.close()


def recv_full_message(sock):
    data = b""
    while True:
        try:
            chunk = sock.recv(4096)
        except socket.timeout:
            break
        except Exception as e:
            print("recv error:", e)
            return None

        if not chunk:
            break

        data += chunk

    if not data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        # maybe it was binary
        return data


try:
    
    Host =  sys.argv[1] #loon.cs.umanitoba.ca
    port = int(sys.argv[2]) #8227

    wsSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    wsSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    wsSocket.bind((Host, port))
    wsSocket.listen()
    print("Webserver is  listening on host - " + str(Host) + ":" + str(port) + "........")
    while True: 
            client_socket, addr = wsSocket.accept()
            print("Received new connection from " + str(addr))
            clientThread = threading.Thread(target= manage_client , args=(client_socket,))
            clientThread.start()


except Exception as e:
    print(e)
finally: 
     print("closing socket")
     wsSocket.close()
