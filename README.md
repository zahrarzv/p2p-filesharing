# p2p-filesharing
Built a multithreaded web server supporting dynamic content and transactional file storage via a 2- Phase Commit (2PC) backend.

p2pFileServer.py: 

this is my peer to peer file server. to start it you must enter the arguments
  
python3 p2pFileServer.py [UMNETID] [HOST] [PORT] [KNOWNHOST] [KNOWNPORT]: 
example: python3 p2pFileSharing.py rizviz loon.cs.umanitoba.ca 8226 silicon.cs.umanitoba.ca 8999
    - its starts with retrieving a maximum of 5 files when it starts and stores them in my files folder. 
    - takes around 15 seconds to successfully download and retrieve messages
    - my delete<id>deletes my local file and sends a delete request to all peers who have the file 
    - for my push command, input push<filename> this should add the filename that already exists in the current directory into my files folder, if it is not on the current directory, it will not be added and will send a respective message. use push hi.txt as an example ( hi.txt must be in the current directory for it to be pushed). once pushed. it sends FILEDATA to a random peer in my peerlist for the file to be added and sends an announce message to all peers
    - get file<id>: this downloads the file from the respective file. if file already present then it just overwrites it. sends an announce message to all peers that i have this file
    -list: this lists all files and their properties that have been collected through gossip/gossip replies and annouce messages or FILE DATA requests
    - peers: lists all peers that are currently on the network through gossip and gossip replies
overall comments: 
- sometimes some requests take a little longer to process, ie 15-20 secs


webserver.py:
both webserver and p2p files must be running for my peers stats page to run successfully 

this file has my webserver code for my peer stats page. USes api end point GET to retreive current file meta data and current peers list. 

python3 webserver.py [HOST] [WEBSERVER PORT] [HOST][P2P PORT]
example: python3 webserver.py loon.cs.umanitoba.ca 8227 loon.cs.umanitoba.ca 8226

VERY IMPORTANT NOTE:
Since Im using a timeout of 10 seconds in my p2p functions please wait about 30’s for the page to refresh each time. lists all the meta data after 30 secs. 

please run the code atleast 3 times to get results, 

webpage.html
: this is just the html code that displays the updates lists each time using the 
webserver's endpoints

go on http://loon.cs.umanitoba.ca:8227/webpage.html to access my webpage



my webserver sends connects to the socket in my parceMessage function and sends the request: "RETURN_FMETADATA" which return a list of all the current files metaData. the metadata list is contructed in my returnfMetaData() function.  similarly it sends the request "RETURN_PEERSLIST" which returns the list of peers. the list of peers is constructed in my getPeersList() function. once i get these two lists i am able buuild a table with my html code using get endpoint. 

periodicPeerCleanup() function removes all the peers that have "time out". it is used in conjunction with my removeOldPeers() function. updates the list of peers 

