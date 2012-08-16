import datetime
from globles import STREET_NAMES

class History() :
    def __init__(self) :
        #self.hand_num = -1
        self.history = []
    
        #dt = str(datetime.datetime.now()).replace(' ','_')[:-7]
        dt = "current"
        self.log = open( "gamelogs/%s.gamelog" % dt, 'w' )


    def __del__(self) :
        self.log.close()

    def newHand(self, player_names, hole_cards) :
        #self.hand_num += 1
        new_hand = {}
        for street in STREET_NAMES :
            new_hand[street] = []

        for pn,hc in zip(player_names,hole_cards) :
            new_hand[STREET_NAMES[0]].append( "    %s : %s" % (pn,hc) )

        self.history.append( new_hand )

    def update(self, street, info) :
        self.history[-1][street].append( info )

    def writeOut(self) :
        for hand_ix in range(len(self.history)) :
            self.log.write("\n\nHand: %d\n" % hand_ix)
            for street in STREET_NAMES :
                self.log.write( "Street %s\n" % street )
                for action in self.history[hand_ix][street] :
                    self.log.write( "   %s\n" % str(action) )
                #some summary info about each street?
        print "writeOut called"
        self.log.close()
