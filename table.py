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
    def __init__(self, num_seats, small_blind=1) :
        self.num_seats = num_seats
        self.num_players = 0
        self.small_blind = small_blind

        #store Player() objects in their relative order 
        self.players = [Player(NA)]*num_seats
        self.player_names = [p.name for p in self.players]
        
        self.button = 0
        self.history = History()
        self.reset()

    #TODO:
    #should be named newHand() ?
    def newHand(self) :
        
        self.advanceButton()
        self.hole_cards = [[FOLDED]*POCKET_SIZE]*self.num_seats
        self.current_bets = [0]*self.num_seats
        self.pot = 0
        #will worry about this bridge when we come to it
        self.side_pot = {}
        self.board = [WILDCARD]*5
        
        self.streets = iter( STREET_NAMES )
        self.street = self.streets.next()

    def registerAction( self, player_ix, action, amount=0 ) :
        if action == 'k' :
            pass
        elif action == 'f' :
            self.hole_cards[player_ix] = [FOLDED]*POCKET_SIZE
        else : #b,c,r
            self.current_bets[player_ix] += amount

        self.history.update( self.street, (player_ix,action,amount) )

    def addPlayer( self, player, ix ) :
        if not self.players[ix].name == NA :
            raise Exception( "someone already sitting there")
        else :
            self.players[ix] = player
            self.player_names[ix] = player.name
            self.num_players += 1

    def chairEmpty( self, ix ) :
        return self.players[ix].name == NA

    #TODO:
    #side-potting?
    #track burned cards
    def advanceStreet( self, cards ) :
        #add the last rounds bets to the pot
        self.pot += sum(self.current_bets)
        #reset
        self.current_bets = [0]*self.num_seats

        if self.street == "undealt" :
            #deal out the hole cards
            cards = iter(cards)
            for pix in range(self.num_seats) :
                if not self.chairEmpty(pix) :
                    self.hole_cards[pix] = cards.next()
        
            human_hole_cards = [makeHuman(hc) for hc in self.hole_cards]
            self.history.newHand(self.player_names, human_hole_cards)

        elif self.street == "preflop" : self.board[:3] = cards
        elif self.street == "flop"    : self.board[3]  = cards[0]
        elif self.street == "turn"    : self.board[4]  = cards[0]

        self.street = self.streets.next()
        
        self.history.update( self.street, makeHuman(self.board) )

    def advanceButton( self ) :
        for pix in range( self.button+1, len(self.players) ) + \
                   range( self.button ) : 
            if not self.players[pix] == NA :
                self.button = pix

    def close(self) :
        self.history.writeOut()



def main() :
    t = Table( num_seats=8 )
    p1 = Player("shake")
    p2 = Player("frylock")
    t.addPlayer(p1, 1)
    t.addPlayer(p2, 2)

    t.reset()

if __name__ == '__main__' :
    main()
