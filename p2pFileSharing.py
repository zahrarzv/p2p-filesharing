

import sys
import select
import json
import socket
import time
import random
import uuid
import hashlib
import re
import functools
import os
import threading 




umNetID = sys.argv[1] #rizviz
thisHost = sys.argv[2]#"loon.cs.umanitoba.ca"
thisPort = int(sys.argv[3]) #8226
gossInterval = 30  # Time between each gossip message (in seconds)
delTime = 60 # time to check if we need to delete peers
peers = {} # list of tracked peers 
# Well-known host for gossiping
knownHost = sys.argv[4] #silicon.cs.umanitoba.ca
knownPort = int(sys.argv[5])# 8999

waitforgoss = 2 # this ensures that we have a few gossip messages/reples before we get initial files
#fileCount = 1
timeout = 60 # this is the number of seconds it takes to check if the peer has left
maxPeer = 5
listofIds = {}

fmetaData = {} # this stores all the files with their repective metadata. 
 # list of peers that have a specific file 
minFiles = 3

def createGossipmessage():
    try: 
        host = thisHost if thisHost != "" else socket.gethostbyname(socket.gethostname())
        gossId = str(uuid.uuid4())
        gossip_message = {
            "type": "GOSSIP",
            "host": host,
            "port": thisPort,
            "id": gossId,
            "peerId": umNetID
        }
        updateIdList(gossip_message) # add your own id to the list
        return gossip_message
    except Exception as e:
        print("exception in createGossipmessage()")
        

def sendRoutineMessages():
    
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as mySocket:
                mySocket.connect((knownHost, knownPort))
                jgoss = createGossipmessage()
                gossipMess = json.dumps(jgoss) + "\n"
                mySocket.send(gossipMess.encode("utf-8"))
                # write how many gossip messages are being sent
            time.sleep(gossInterval)
        except Exception as e:
            print("Exception in sending gossip:", e)

   
        
def parceCommand(command):

    try:
        if len(command) == 1:
            if command[0] == "list":
                listFiles()
            elif command[0] == "exit":
                print("exiting program...")
                os._exit(0)
            elif command[0] == "peers":
                listPeers(peers)
        elif len(command) == 2: 
            if command[0] == "push":
                pushFile(command[1]) 
            elif command[0] == "get":
                getFile(command[1])
            elif command[0] == "delete":
                delete(command[1])
    
    except Exception as e: 
        print("Exception in parceCommand, ", e)


def deleteMessage(fileId):
    try:
        deleteMess = {
        "type": "DELETE",
        "from": umNetID,
        "file_id": fileId
        }
        return deleteMess 
    except Exception as e:
        print(f"exception occured in deleteMessage(): {e}")





def delete(fileid): 

    try:
            fileIdExists = fmetaData.get(fileid) # get the id 
            if fileIdExists: # if you get a valid id 
                if fileIdExists.get("Owner") == umNetID:
                    # then 
                    deleteMessageReceived(umNetID, fileid)
                    try:
                        eligiblePeersList = [p for p in fileIdExists["peersWithfiles"] if p != umNetID]
                        if not eligiblePeersList:
                            print("No other peers have that file right now.")
                            return
                        for peer in peers.values():
                            if peer.get("peer_id") in eligiblePeersList:
                                host = peer.get("phost") 
                                port = peer.get("port")
                                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                                    s.connect((host, port))
                                    jstring = json.dumps(deleteMessage(fileid))
                                    s.send((jstring + "\n").encode("utf-8"))
                        print("send delete request to all peers with files")
                    except Exception as e: 
                        print(f"An exception occurred while trying to send delete messgae(): {e}")
                else: 
                    print("You are not the owner of this file so, you cannot delete it :( ")
            else: 
                print("this id does not exist")
    except Exception as e: 
        print(f"An exception was thrown in delete(fileid) - {e}")




        
def deleteMessageReceived(peerid, fileid):
    global fmetaData
    Folder = os.path.join(os.getcwd(), "files")
    try:
        fileIdExists = fmetaData.get(fileid)
        if fileIdExists: 
            owner   = fileIdExists.get("Owner")
            filename = fileIdExists.get("filename")
            if peerid == owner: 
               path = os.path.join(Folder, filename)
               os.remove(path) # this deletes the file from the file path
               del fmetaData[fileid]
               print(f"{filename} has successfully been deleted")

            else: 
               print(f"{peerid} is not the owner of {filename}. File cannot be deleted. ")
        else: 
            print ("file does not exist in metadata")
    
    except Exception as e: 
        print(f"found an exception deleteMessageReceived {e}")

    


    




def createGetMessage(fileid):
    try:
        jMess = {
            "type": "GET_FILE",
            "file_id": fileid 
            }
        return jMess
    except Exception as e:
        print("exception in createGetMessage()")

def pushFile(path): 
    try:
        if os.path.exists(path): # if the file is on the current working directory, only then are you allowed to push it
            filesFolderPath = os.path.join(os.getcwd(), "files")
            os.system(f"cp '{path}' '{filesFolderPath}/'")
            size = os.path.getsize(path)
            filename = os.path.basename(path)
            fileTimeStamp=time.ctime(int(os.path.getmtime(path)))
        
            with open(path, 'rb') as f:
                rawBytes = f.read()

            h = hashlib.sha256()
            h.update(rawBytes)                            
            h.update(str(fileTimeStamp).encode('utf-8'))    
            file_id = h.hexdigest()

            jAnnounce = {
            "type": "ANNOUNCE",
            "from": umNetID,
            "file_name": filename,
            "file_size":size,
            "file_id": file_id,
            "file_owner": umNetID,
            "file_timestamp": time.ctime(int(os.path.getmtime(path)))}
            try:
                addMetaDataList(file_id, filename, umNetID, size, fileTimeStamp, [umNetID])
            except Exception as e: 
                print(f"unable to add file to metaData {e}")
            
            # choose a peer
            eligiblePeers = [
            peer_info
            for peer_info in peers.values()
            if peer_info.get("peer_id") != umNetID
            ]
            if not eligiblePeers:
                print("No other peers to push to.")
                return

            selectedPeer = random.choice(eligiblePeers)
            selhost = selectedPeer["phost"]
            selPort  = selectedPeer["port"]
            selPid   = selectedPeer["peer_id"]
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.connect((selhost, selPort))
                        parceGetFileCommand(file_id,s)
                        print(f"file sent to one of the tracked peers: {selPid}")
            except Exception as e: 
                print(f"unable to send FILE_DATA to {selPid}")
        
            for peer in list(peers.values()): 
                host = peer.get("phost")
                port = peer.get("port")
                peerID = peer.get("peer_id")
                try: 
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.connect((host, port))
                        jstring = json.dumps(jAnnounce)
                        s.send((jstring + "\n").encode("utf-8"))
                except Exception as e:
                    print(f"unable to send Announce message {e}")
            print(f"Pushed {filename}, Announce Message sent to all peers")

        else: 
            print("This file is not on the current directory. Files must be on the current directory in order to push them")
    except Exception as e: 
        print(f"Exception occurred in pushFile() {e} ")



def getFile(fileid):
    try:
          
        foundId = fmetaData.get(fileid)
        if not foundId:
            print("Id is not valid")
            return
            

        # all peers except me
        eligiblePeers = [p for p in foundId["peersWithfiles"] if p != umNetID]
        if not eligiblePeers:
            print("No other peers have that file right now.")
            return

        selectedPeerId = random.choice(eligiblePeers)
        for peer in peers.values():
            if peer.get("peer_id") == selectedPeerId:
                host = peer.get("phost") 
                port = peer.get("port")
                break 
    
    
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
           # s.settimeout(5) 
            s.connect((host, port))
            jstring = json.dumps(createGetMessage(fileid))
            s.send((jstring + "\n").encode("utf-8"))


            recvFileMd = recv_full_message(s)
            if not recvFileMd:
                print(f"No response or invalid data from peer {selectedPeerId}.")
                return

            try:
                jMess = json.loads(recvFileMd)
            except json.JSONDecodeError as e:
                print(f"Invalid JSON received from peer: {selectedPeerId}")
                return
        
            jMess = json.loads(recvFileMd) # load the dictionary
            decode(jMess, selectedPeerId)
        
            
    except Exception as e: 
        print("exception found in getFile()", e)

def decode(jMess, peerid): 

 
    data_hex = jMess.get("data")
    if not data_hex:
        print(f"No data field in FILE_DATA response; skipping decode.This is coming from{peerid}")
        return

    try:
        file_bytes = bytes.fromhex(data_hex)
    except ValueError as e:
        print("Invalid hex data:", e)
        return
    try:
        file = {
        "file_name": jMess.get('file_name'),
        "file_size": jMess.get('file_size'),
        "file_id": jMess.get('file_id'),
        "file_owner": jMess.get('file_owner'),
        "file_timestamp": jMess.get('file_timestamp')
        }
        

        fileContent = bytes.fromhex(jMess.get("data"))
        path = os.path.join("files", jMess.get("file_name"))
        with open(path, "wb") as f:
            f.write(fileContent)
            print("successfully downloaded " + jMess.get("file_name"))
        addMetaData(file ,peerid)
        
        jAnnounce = {
                "type": "ANNOUNCE",
                "from": umNetID,
                "file_name":  jMess.get('file_name'),
                "file_size":jMess.get('file_size'),
                "file_id": jMess.get('file_id'),
                "file_owner": jMess.get('file_owner'),
                "file_timestamp": time.ctime(int(os.path.getmtime(path)))}
        for peer in list(peers.values()): 
            host = peer.get("phost")
            port = peer.get("port")
            peerID = peer.get("peer_id")
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((host, port))
                    jstring = json.dumps(jAnnounce)
                    s.send((jstring + "\n").encode("utf-8"))
        
            except Exception as e:
                print(f"unable to send Announce message {e}") 
        print("sent Announce Message to all peers")
    except Exception as e: 
        print("exception thrown in decode function", e)



def updateIdList(pJdict):
    try:
        gossId = pJdict.get("id")
        peerId = pJdict.get("peerId")
        
        idDetails = {
            "peerId": peerId,
            "gossId" :gossId
        }


        listofIds[gossId] = idDetails
    except Exception as e: 
        print("Exception in updatedList")




def listPeers(peers):
    try:
        for peer in peers.values():
            peer_id = peer.get("peer_id")
            host, port = (peer.get("phost"), peer.get("port"))
            last_seen = time.ctime(peer.get("time"))
            print(f"{peer_id} at {host}:{port}, last seen: {last_seen}")
    except Exception as e:
        print("Exception in listPeers")






def recv_full_message(sock):
    sock.settimeout(15)
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


        
    except Exception as e:
        print("exception in recv_full_message", e)


def handleGossipReply(peerSocket): # this is the function where you recieve all the gossip replies
    try:
        
        gossReply = recv_full_message(peerSocket)
        if gossReply:
            #print(gossReply)
           parceMessage(gossReply,peerSocket)

    #{"type": "GOSSIP_REPLY", "host": "130.179.28.127", "port": 8040, "peerId": "sbedi", "files": [{"file_name": "saulo-profile-s.jpeg", "file_size": 0.019560813903808594, "file_id": "aa3d87025fe45ff8af821a03f73590c75bb832ec20c4e6690a66cc105ed02953", "file_owner": "bedis3", "file_timestamp": 1743801128}]}
   # Received from peer: {"type": "GOSSIP", "host": "cormorant.cs.umanitoba.ca", "port": 8230, "id": "64a4f5b2-f330-443c-b5e9-e2001cbfe76f", "peerId": "sanons"}

    except Exception as e:
        print("Exception in handleGOssipReply")
    finally:
        peerSocket.close()

def updatePeerList(peerJdict):
    try: 
        global peers
        peerId = peerJdict.get("peerId")
        peerHost = peerJdict.get("host")
        id_p = peerJdict.get("id")
        # id_list.append(id_p)
        peerPort = peerJdict.get("port")
        lastSeen = time.time()

        peers_string = {
            "peer_id": peerId,
                "phost": peerHost,
                "port": peerPort,
                "time": lastSeen
                
            }

        peers[(peerHost, peerPort)] = peers_string
    except Exception as e: 
        print("exception in updatePeerList")

def getPeersList(): 
    try:
        peer_list = []
        for peer in peers.values():
             peer_list.append({
                 "peer_id":  peer["peer_id"],
                 "host":     peer["phost"],
                 "port":     peer["port"],
                 "last_seen": time.ctime(peer["time"])
             })
        return peer_list
    except Exception as e: 
        print(f"Exception occurred in {e}")

def removeOldPeers(peers):

    try:
        currentTime = time.time()
        oldPeers = [peer for peer, peer_details in peers.items() if (currentTime - peer_details["time"]) > timeout]
        for peer in oldPeers:
            del peers[peer]
    except Exception as e: 
        print("Exception in removeOldPeers")

def periodicPeerCleanup(delTime):
    try:
      removeOldPeers(peers)
      threading.Timer(delTime, periodicPeerCleanup, [delTime]).start()
    except Exception as e: 
        print("error in PeriodicPeerCleanup()")

def listFiles(): 

    try: 
        for file in fmetaData.values():
            file_id = file.get("fileId")
            filename = file.get("filename")
            peerswFiles = file.get("peersWithfiles",[])
            peers_str = ", ".join(peerswFiles)
            print(f"{file_id} : {filename} - Peers: {peers_str}")  

    except Exception as e: 
        print("Error in listFiles: ", e)

def returnfMetaData():
    try:
        fMetaData_list = []
        for data in fmetaData.values():
            timeString = data["fileTime"]
            if isinstance(timeString, (int, float)):
                String = time.ctime(timeString)
            else:
                # assume it’s already a human‐readable string
                String = timeString
    
        fMetaData_list = []
        for data in fmetaData.values():
            fMetaData_list.append({
                 "fileId":  data["fileId"],
                 "filename":     data["filename"],
                 "Owner":     data["Owner"],
                 "filesize":data["filesize"],
                 "fileTime": String,
                 "peersWithfiles":data["peersWithfiles"]
            })
        return fMetaData_list
    except Exception as e: 
        print(f"Exception occurred in {e}")

def addMetaData(files, peerId):
   
    try:
        global fmetaData

        for file_info in files:
            # check it's actually a dict
            if not isinstance(file_info, dict):
               # print("Skipping non-dict in addMetaData:", file_info, peerId)
                continue

            file_id = file_info.get("file_id")
            if not file_id:
                print("Skipping entry without file_id:", file_info)
                continue

            if file_id in fmetaData:
                peers_with = fmetaData[file_id]["peersWithfiles"]
                if peerId not in peers_with:
                    peers_with.append(peerId)
            else:
                addMetaDataList(file_id,file_info.get("file_name"),file_info.get("file_owner"),file_info.get("file_size"),file_info.get("file_timestamp"),[peerId])
           
    except Exception as e: 
        print ("something went wrong in addMetaData()", e)

def addMetaDataList(fileid, fname, owner,filesize, fileTime, peersWithfiles):
    global fmetaData
    fmetaData[fileid]= {
        "fileId": fileid, 
        "filename":fname, 
        "Owner":owner, 
        "filesize":filesize,
        "fileTime":fileTime, 
        "peersWithfiles": peersWithfiles
    }



def createGossipReply(Ohost, OPort):
    host = thisHost if thisHost != "" else socket.gethostbyname(socket.gethostname())
    #getJsonString = json.dumps(getStoredFiles())
    try:
        gossip_message = {
                "type": "GOSSIP_REPLY",
                "host": host,
                "port": thisPort,
                "peerId": umNetID,
                "files": getStoredFiles()
                }
    except Exception as e: 
        print(f"error in CreateGossipReply {e}")
    return gossip_message




def getStoredFiles():
        JsonFileDict   = []
        filesFolderPath = os.path.join(os.getcwd(), "files")

        try:
            for fname in os.listdir(filesFolderPath):
                filePath = os.path.join(filesFolderPath, fname)
                if not os.path.isfile(filePath):
                    continue

               
                with open(filePath, 'rb') as f:
                    rawBytes = f.read()

                
                fileSize      = os.path.getsize(filePath)
                fileTimeStamp = int(os.path.getmtime(filePath))

               
                h = hashlib.sha256()
                h.update(rawBytes)                            
                h.update(str(fileTimeStamp).encode('utf-8'))    
                file_id = h.hexdigest()
                # owner = file_id.get("Owner")
                owner = fmetaData.get(file_id, {}).get("Owner", umNetID)
                # 4) Build the metadata dict
                JsonFileDict.append({
                    "file_name":      fname,
                    "file_size":      fileSize,# change this 
                    "file_id":        file_id,
                    "file_owner":     owner, # change rhis 
                    "file_timestamp": fileTimeStamp
                })

            return JsonFileDict

        

        except Exception as e: 
            print(f"Line = 116:{e} ")        
         

def forwardTopeers(gossReply):

    Ohost = gossReply.get("host")
    oPort = gossReply.get("port")
    umnet = gossReply.get("peerId")

    eligiblePeers = [
        (host, port)
        for (host, port) in peers.keys()
        if (host, port) != ( Ohost, oPort)
    ]

    numForward = min(maxPeer, len(eligiblePeers))
    peersSel = random.sample(eligiblePeers, numForward)
    jString = json.dumps(gossReply)
    
    for (host, port) in peersSel:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((host, port))
                s.send(jString.encode('utf-8'))
               # print(f"Forwarded gossip to {host}:{port}")
        except Exception as e:
            continue
           # print(f"Failed to forward gossip to{umnet} {host}:{port} — {e}")

def getInitialFiles(): 

    try:
       # addMetaData(getStoredFiles(), umNetID)
        start = time.time()
        # 1) Poll until we have enough metadata or we hit the timeout
        print("waiting to load initial files.........")
        while time.time() - start < 2:
            if len(fmetaData) >= minFiles :
                break
            time.sleep(1)

        # 2) If after waiting we still know nothing, skip bootstrap
        if not fmetaData:
            print("No files known after waiting.")
            return

        # add your own file to your list of metaData upon enter
        ids = list(fmetaData.keys())
        random.shuffle(ids)
        to_download = ids[:min(5, len(ids))]

        for fid in to_download:
            print(f"trying to  download the file with id:  {fid} …")
            getFile(fid)
    except Exception as e: 
        print("Exception in getInitialFiles()")



def  parceMessage(gossReply, psocket):
     
    try:   
            try:
        # Convert the JSON string to a Python object
                parsed = json.loads(gossReply)
            except json.JSONDecodeError as e:
                print("Invalid JSON received:", e)
                return

    
            if isinstance(parsed, list):
                jReply = parsed[0]
            else:
                jReply = parsed


#if you get a gossip message with a different gossId then 
#update that peerList
# updateIdlist() put the new gossipID in my new peersList 
            if jReply.get("type") == "GOSSIP" and not gossIdExists(jReply.get("id")): 
                originHost = jReply.get("host")
                originPort = jReply.get("port")
                updatePeerList(jReply)
                updateIdList(jReply)
                forwardTopeers(jReply)
                jdictMessage = createGossipReply(originHost, originPort)
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as mySocket:
                        mySocket.connect((originHost, originPort))
                        

                        gossipReplyMess = json.dumps(jdictMessage) 
                        mySocket.send(gossipReplyMess.encode("utf-8"))
                        

                except Exception as e:
                        return
                    #print("this is an error" +originHost, originPort, e)
                
        
            elif jReply.get("type") == "GOSSIP_REPLY" and not gossIdExists(jReply.get("id")):
                updatePeerList(jReply) # update the peer
                addMetaData(jReply.get("files"), jReply.get("peerId"))

            elif jReply.get("type") == "GET_FILE":
                 parceGetFileCommand(jReply.get("file_id"), psocket)
            
            elif jReply.get("type") == "ANNOUNCE":
                 addMetaDataList(jReply.get("file_id"),jReply.get("file_name"),jReply.get("file_owner"),jReply.get("file_size"),jReply.get("file_timestamp"),[jReply.get("from")])
                 peerSender = jReply.get("from")
                 print(f"Recieved Announce from {peerSender}")
            
            elif jReply.get("type") == "DELETE":
                 deleteMessageReceived(jReply.get("from"), jReply.get("file_id"))
        
            elif jReply.get("type") == "FILE_DATA":
                decode(jReply, jReply.get("file_owner"))
            
            elif jReply.get("type") == "RETURN_FMETADATA":
                  psocket.sendall((json.dumps(returnfMetaData()) + "\n").encode("utf-8"))
           
            elif jReply.get("type") == "RETURN_PEERSLIST":
                  psocket.sendall((json.dumps(getPeersList()) + "\n").encode("utf-8"))


     
    except Exception as e: 
            print(f"exception in ParceMessage {e}")
def invalidFile():
    try:
        Jmess = {
            "type": "FILE_DATA",
            "file_name": "null",
            "file_size": "null",
            'file_id': "null",
            "file_owner": "null",
            "file_timestamp": "null",
            "data": "null"
            }
        return jmess
    except Exception as e: 
        print(f"exception in invalidFile():  {e}")


def parceGetFileCommand(file_id, socket):
    try:
        filefound = fmetaData.get(file_id)
        if not filefound:
           stringsend = json.dumps(invalidFile() + "\n")
        else:

            fname   =filefound ["filename"]
            size    = filefound ["filesize"]
            owner   = filefound ["Owner"]
            fileTs  = filefound ["fileTime"]

            # read the bytes
            path = os.path.join("files", fname)
            with open(path, "rb") as f:
                content = f.read()

            hexContent = content.hex()

            Jmess = {
                "type":           "FILE_DATA",
                "file_name":      fname,
                "file_size":      size,
                "file_id":        file_id,
                "file_owner":     owner,
                "file_timestamp": fileTs,
                "data":           hexContent
            }
            stringsend = json.dumps(Jmess) + "\n"
            print("successfully sent file:" + fname)


        try:
            jstring = stringsend
            socket.sendall(jstring.encode("utf-8"))
            #print("successfully sent file:" + fname)
        except Exception as e: 
            return
           # print("Unable to send file Details")
             
    except Exception as e:
        print("exception in ParceGetFileCommand()", e)       
                
def gossIdExists(id): 
    try:
        return any(info.get("gossId") == id for info in listofIds.values())
    except Exception as e: 
        print("error in gossIdExists")



def command_loop():
    # This loop handles user commands
    try:
        while True:
            command = input("use list - List files from metadata\npeers - Show tracked peers\npush <Path> - Upload a file with peerId as owner\nget <fileId> - Download a file to local files\ndelete <fileId> - Delete a file (if you’re the owner)\nexit - Exit the program\nEnter Command: \n")
            if command:
                cSplit = command.split()  # Convert command into a list of arguments
                parceCommand(cSplit)
    except Exception as e: 
        print("exception in command loop")
def accept_connections(wsSocket):
    # This loop continuously accepts new connections
    while True:
        try:
            clientSocket, addr = wsSocket.accept()
            clientThread = threading.Thread(target=handleGossipReply, args=(clientSocket,), daemon=True)
            clientThread.start()
        except Exception as e:
            print("Exception in accept_connections:", e)



def getReplies():

    try:
        periodicPeerCleanup(delTime)
        host = thisHost if thisHost != "" else socket.gethostbyname(socket.gethostname())
        wsSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        wsSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        wsSocket.bind((host, thisPort))
        wsSocket.listen()
        print("Peer " + umNetID + " running on " + host + ":" + str(thisPort))
        
        # Start the accept_connections thread to handle incoming messages
        threading.Thread(target=accept_connections, args=(wsSocket,), daemon=True).start()
        #threading.Thread(target=lambda: getInitialFiles(), daemon=True).start()
        getInitialFiles()

        # Run the command loop in the main thread (or you can also run it in another thread)
        command_loop()
    except Exception as e:
        print(f"exception in getReplies() {e} ")



if __name__ == "__main__":
    # Start the outgoing gossip thread

    gossip_thread = threading.Thread(target=sendRoutineMessages)
    gossip_thread.daemon = True
    gossip_thread.start()
    # Run the server to handle incoming connections from peers
    getReplies()

