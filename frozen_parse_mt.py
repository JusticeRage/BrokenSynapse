import sys
import struct


class MTHeader:
    def __init__(self, header):
        splitted = header.split("\t")
        self.id = int(splitted[0])  # Game ID
        self.opponent = splitted[2]
        self.currentGSEPSide = splitted[3]  # Which "side" belongs to the player.
        self.turn = int(splitted[4])
        self.committed = splitted[5] == "1"
        self.info = splitted[6]
        self.bidding_phase = splitted[7] == "1"
        self.finished = splitted[8] == "1"
        self.spectating = splitted[9] == "1"
        self.opponent_spectating = splitted[10]  # Name of the player being "replaced" when spectating
        self.declined = splitted[11] == "1"
        self.rating = float(splitted[12])
        self.vs_record = [int(s) for s in splitted[13].split(" ")]
        self.p1_record = [int(s) for s in splitted[14].split(" ")]
        self.p2_record = [int(s) for s in splitted[15].split(" ")]
        self.p1_rank = int(splitted[16])
        self.p2_rank = int(splitted[17])
        self.p1_level = int(splitted[18])
        self.p2_level = int(splitted[19])
        self.player1 = splitted[20]
        self.player2 = splitted[21]
        self.score = float(splitted[22])
        self.timed_turns = not self.finished and int(splitted[23])
        self.timed_turns_time = int(splitted[24])
        self.opponent_committed = splitted[25] == "1"

    def __str__(self):
        s = "Game %s " % self.id
        if self.finished:
            s += "(finished with a score of %.2f in %s turns)\n" % (self.score, self.turn)
        else:
            s += "(currently in turn %s" % self.turn
            if self.committed:
                s+= " - turn primed)\n"
            elif self.opponent_committed:
                s+= " - opponent turn primed)\n"
            else:
                s+= ')\n'
        s += "Player 1: %s (Rank: %d - Level: %s - Wins: %s - Losses: %s)\n" \
            % (self.player1, self.p1_rank, self.p1_level, self.p1_record[0], self.p1_record[1])
        s += "Player 2: %s (Rank: %d - Level: %s - Wins: %s - Losses: %s)\n" \
            % (self.player2, self.p2_rank, self.p2_level, self.p2_record[0], self.p2_record[1])
        s += "Match history: %s won %d time(s) and %s won %d time(s)." \
            % (self.player1, self.vs_record[0], self.player2, self.vs_record[1])
        return s


def parse_mt(path):
    with open(path, 'rb') as f:
        if f.read(4) != "\x06\x00\x00\x00":
            print "Wrong magic!"
            return

        header_size, = struct.unpack("B", f.read(1))
        if header_size > 0:
            header = f.read(header_size)
            h = MTHeader(header)
            print h

        """if not skip_zero(f): return
        number_of_units, = struct.unpack("L", f.read(4))
        if not skip_zero(f): return
        print "Number of units: %d" % number_of_units
        for i in range(0, number_of_units):
            type_size, = struct.unpack("xB", f.read(2))
            type = f.read(type_size)
            print hex(f.tell())
            team, = struct.unpack(">2xL12x", f.read(18))
            waypoints, x, y = struct.unpack("l8x2f8x", f.read(28))
            print "%s (Player %d, X=%f, Y=%f, WP=%d)" % (type, team, x, y, waypoints)
            f.read((waypoints - 1) * 22) # Burn waypoint info for now
            print f.tell()"""

if __name__ == "__main__":
    parse_mt(sys.argv[1])