from history import History
from player import Player
from globles import NA, STREET_NAMES, FOLDED, WILDCARD, POCKET_SIZE
from deck import makeHuman

# for storing information about the state of the game

# a Dealer() will arbitrate over the Table() object to direct the game
# have separated these things because when it comes time to gamble, the Dealer()
# class will be out of our control, but we'll want to be keeping track of the 
# game

# basically, assume all alterations to the Table() are valid
# as they are controlled by our Dealer() class, or the poker site client

#not active
# decorator macro
# as the players take actions, we want to update the History()
# this function wraps each action, so that if any one gets invoked
# the History is automatically updated
#def updateHistory( func ) :
    #def inner( *args ) : 
        #action = func( *args )
       # 
        ##TODO:
        ##add all the relevant Table info to action
        #relevant_stuff = 42
#
        #args[0].history.update( relevant_stuff, action )
    #return inner

   

class Table() :
    def __init__(self, \
                 players, \
                 stacks, \
                 toby_ix, \
                 pockets, \
                 button=0, \
                 logging=False, \
                 small_blind=1) :

        self.small_blind = small_blind
        self.logging = logging

        self.toby_ix = toby_ix
        self.stacks = stacks

        #store Player() objects in their relative order 
        #self.players = [Player(NA)]*num_seats
        self.players = players
        self.player_names = [p.name for p in self.players]
        self.num_players = len(players) 
        
        self.button = button
        if self.logging :
            self.history = History()
        else :
            self.history = {}
            for s in STREET_NAMES :
                self.history[s] = []
        self.newHand(pockets)

    def __str__(self) :
        r = []
        r.append( "Table:" )
        r.append( "    Player Names: %s" % '; '.join(self.player_names) )
        pocks = [str(makeHuman(p)) for p in self.pockets]
        r.append( "    Pockets: %s" % '; '.join(pocks) )
        r.append( "    Stacks: %s" % '; '.join([str(s) for s in self.stacks]) )
        r.append( "    Button: %s" % self.player_names[self.button] )
        r.append( "    Street: %s" % self.street )
        r.append( "    Board: %s" % ' '.join(makeHuman(self.board)) )
        r.append( "    Pot: %d" % self.pot )
        r.append( "    Current Bets: %s" % \
                       "; ".join([str(cb) for cb in self.current_bets]) )
        r.append( "    Action To: %s" % self.player_names[self.action_to] )
        return "\n".join( r )

    #TODO:
    #should be named newHand() ?
    def newHand(self,pockets) :
        
        self.advanceButton()
        self.pockets = pockets #[deck.draw(2) for i in range(self.num_players)]
        #self.pockets = [[FOLDED]*POCKET_SIZE]*self.num_players
        self.folded = [False]*self.num_players
        self.acted = [False]*self.num_players
        self.current_bets = [0]*self.num_players
        self.committed = [0]*self.num_players
        self.pot = 0
        #will worry about this bridge when we come to it
        self.side_pot = {}
        self.board = makeHuman([WILDCARD]*5)
        
        self.streets = iter( STREET_NAMES )
        self.street = self.streets.next()
        self.street = self.streets.next()

    def possibleRaises( self, player_ix, fractions ) :
        possible = []
        #print "possRaise pix:", player_ix
        for frac in fractions :

            #print "frac*self.pot", frac, frac*self.pot
            #print "oblig", self.getObligation(player_ix)
            #print "stack", self.stacks[player_ix]
            if frac * self.pot + self.getObligation(player_ix) <= \
               self.stacks[player_ix] :
                possible.append(frac)
        return possible

    def updateStack( self, player_ix, amount ) :
        self.current_bets[player_ix] += amount 
        self.stacks[player_ix]       -= amount
        self.committed[player_ix]    += amount

    def registerAction( self, action, fraction=False ) :
        player_ix = self.action_to

        if action == 'k' :
            pass
        elif action == 'f' :
            self.folded[player_ix] = True
            #self.current_bets[player_ix] = -1
        else : #b,c,r
            #consider making these three operations atomic
            #make the call
            oblig = self.getObligation(player_ix)
            self.updateStack( player_ix, oblig )

            if self.stacks[player_ix] < 0 :
                print "WHOA THERE STACK IS NEGATIVE"
                #credit the amout back to committed players
                cur_bet = self.current_bets[player_ix]
                adj_amt = self.stacks[player_ix]
                for pix in range(self.num_players) :
                    diff = abs(self.current_bets[pix] - cur_bet)
                    if diff <= .001 :
                        self.updateStack( pix, adj_amt )
                #TODO: form a side pot

            #make the raise  
            if action == 'r' :
                raise_amt = fraction * self.pot
                self.updateStack( player_ix, raise_amt )
                assert self.stacks[player_ix] >= 0

        if self.logging :
            self.history.update( self.street, (player_ix,action,amount) )
        else :
            self.history[self.street].append( action )

        self.acted[player_ix] = True
        self.action_to = self.ringIncrement( self.action_to )

    def ringIncrement( self, i ) :
        if i == self.num_players-1 :
            return 0
        else : return i+1

    def addPlayer( self, player, ix ) :
        if not self.players[ix].name == NA :
            raise Exception( "someone already sitting there")
        else :
            self.players[ix] = player
            self.player_names[ix] = player.name
            self.num_players += 1

    def chairEmpty( self, ix ) :
        return self.players[ix].name == NA

    def getObligation( self, player_ix ) :
        #return the first non-zero current-bet of a non-folded player
        ixs = range( player_ix-1, -1, -1) + \
              range( self.num_players-1, player_ix, -1)
        for ix in ixs :
            is_folded = self.folded[ix]
            if not is_folded :
                diff = self.current_bets[ix] - \
                       self.current_bets[player_ix]
                assert diff >= 0
                return diff
        #everyone has folded
        return 0

    def collectBets( self ) :
        #add the last rounds bets to the pot
        self.pot += sum(self.current_bets)
        #reset
        self.current_bets = [0]*self.num_players
        self.acted = [False]*self.num_players

    #TODO:
    #side-potting?
    #track burned cards
    def advanceStreet( self, cards ) :
        self.collectBets()
        if self.street == "undealt" :
            #deal out the hole cards
            cards = iter(cards)
            for pix in range(self.num_seats) :
                if not self.chairEmpty(pix) :
                    self.pockets[pix] = cards.next()
                    #deck.draw(POCKET_SIZE)
        
            human_pockets = [makeHuman(hc) for hc in self.pockets]
            
            if self.logging :
                self.history.newHand(self.player_names, human_pockets)


        elif self.street == "preflop" : self.board[:3] = cards
        elif self.street == "flop"    : self.board[3]  = cards[0]
        elif self.street == "turn"    : self.board[4]  = cards[0]

        self.street = self.streets.next()
        self.action_to = self.ringIncrement( self.button )
        
        if self.logging :
            self.history.update( self.street, makeHuman(self.board) )

    def advanceButton( self ) :
        for pix in range( self.button+1, len(self.players) ) + \
                   range( self.button ) : 
            if not self.players[pix] == NA :
                self.button = pix
                self.action_to = self.ringIncrement( self.button )
                #action_to = self.button+1
                #if action_to == len(self.players) :
                    #self.action_to = 0
                #else :
                    #self.action_to = action_to

    def close(self) :
        if self.logging :
            self.history.writeOut()



def main() :
    t = Table( num_seats=8 )
    p1 = Player("shake")
    p2 = Player("frylock")
    t.addPlayer(p1, 1)
    t.addPlayer(p2, 2)

    #t.newHand()

if __name__ == '__main__' :
    main()
