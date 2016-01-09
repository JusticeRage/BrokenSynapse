#!/bin/python

import hashlib
import socket
import zlib
import sys

HOST = "62.197.39.230"
PORT = 28021

ACTIVE_GAMES = []


def hash_password(password, salt):
    return hashlib.md5(salt + hashlib.md5(password).hexdigest().upper()).hexdigest().upper()


def handle_writefile(s, commandline):
    data = s.recv(10000)
    decompress = zlib.decompressobj(-zlib.MAX_WBITS)
    filename = commandline.split("\t")[1]
    s.send("fileFinished\t%s" % filename)

    # Handle special files
    if filename == "psychoff/rankings.txt": # Online players
        lines = decompress.decompress(data).split("\n")
        print "%s online players: " % lines[0]
        for line in lines[1:]:
            print "\t%s (%s)" % (line.split("\t")[0], line.split("\t")[1])
        return

    if filename == "psychoff/activeGames.txt": # Active games
        game_list = decompress.decompress(data).split("\n")
        if len(game_list) > 1:
            print "Active games:"
            for line in game_list[1:]:
                game_details = line.split("\t")
                print "\t%s against %s (#%s)" % (game_details[2], game_details[1], game_details[0])
                ACTIVE_GAMES.append(game_details[0])
                return

    if filename.endswith(".enc"):
        print "Dumping MultiTurn data."
        with open("testMT.enc", "w") as f:
            f.write(data)
        return

    return decompress.decompress(data)


def login(s, username, password):
    s.send("textcom\tprelogon\n")
    salt_rec = s.recv(1024)
    salt = salt_rec.split("\t")[-2]
    s.send("textcom\tlogin\t%s\t%s\t33\n" % (username, hash_password(password, salt)))
    logged_in = s.recv(1024)
    if "loggedIn" in logged_in:
        print "*** Successfully logged in as %s!" % username
        return True
    else:
        print "[!] Error: could not log in: %s." % logged_in
        return False


s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))
if not login(s, "[username]", "[password]"):
    sys.exit(-1)

s.send("textcom\tcommand\tsetMyOS\twindows.steam\n")
s.send("textcom\tcommand\trefreshPeopleOnline\n")
s.send("textcom\tcommand\trequestHomeScreen\n")  # Request home screen messages
# s.send("textcom\tcommand\tselectMT\t[game ID]\n")

while True:
    data = s.recv(1024)
    requests = data.split("\n")
    for request in requests:
        if not request: continue

        splitted = request.split("\t")

        if splitted[0] == "writeFile":
            read = handle_writefile(s, request)
            if read:
                print "File received: %s:\n----------\n%s\n----------" % (request.split("\t")[1], read)

        elif splitted[0] == "textcom" and splitted[1] == "command":
            if splitted[2] == "setMyStats":
                print "You are currently level %s." % splitted[3]
            elif splitted[2] == "HasDLCStatus":
                print "Red DLC is activated for your account!" if splitted[3] == "1" else "Red DLC is not activated for your account."
            elif splitted[2] == "ping":
                print "* Server ping *"
            elif splitted[2] == "ack" or splitted[2] == "SetSocketMode" or splitted[2] == "oppDisplayStatusChanged":
                continue
            else:
                print "*** Received: %s" % request

        else:
            print "*** Received: %s" % request