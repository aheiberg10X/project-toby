import deck
import history
from player import Player

# for storing information about the state of the game

# a Dealer() will arbitrate over the Table() object to direct the game
# have separated these things because when it comes time to gamble, the Dealer()
# class will be out of our control, but we'll want to be keeping track of the 
# game

# basically, assume all alterations to the Table() are valid
# as they are controlled by our Dealer() class, or the poker site client

#not active
NA = 'xx'

# decorator macro
# as the players take actions, we want to update the History()
# this function wraps each action, so that if any one gets invoked
# the History is automatically updated
def updateHistory( func ) :
    def inner( *args ) : 
        action = func( *args )
        
        #TODO:
        #add all the relevant Table info to action
        relevant_stuff = 42

        args[0].history.update( relevant_stuff, action )
    return inner

class Table() :
    def __init__(self, num_seats) :
        self.deck = deck.Deck()
        self.num_seats = num_seats
  
        #order is relevant
        self.players = [NA]*num_seats
        self.hole_cards = [NA]*num_seats
        self.current_bets = [0]*num_seats
        
        self.button = 0
        self.pot = 0
        #will worry about this bridge when we come to it
        self.side_pot = {}
        self.board = ['__']*5
        
        #0:preflop, 1:flop, 2:turn, 3:river
        self.street = 0

        self.history = history.History()


    ####################################################
    #### Actions
    ####################################################

    @updateHistory
    def fold( self, player_ix, amount=42 ) :
        self.hole_cards[player_ix] = "xx"
        return ('f',player_ix,amount)

    def bet( self, player_ix, amount ) :
        return ('b',player_ix,amount)

    def call( self, player_ix, amount ) :
        return ('c',player_ix,amount)

    def raze( self, player_ix, amount ) :  #raise is a keyword
        return ('r',player_ix,amount)

    ######################################################
    #### End Actions
    ######################################################

    #put in pot
    def pip( self, player_ix, amount ) :
        self.current_bets[player_ix] += amount

    def addPlayer( self, player, ix ) :
        assert self.players[ix] == NA
        self.players[ix] = player

    #TODO:
    #side-potting?
    def advanceStreet( self, cards ) :
        self.pot += sum(self.current_bets)
        self.current_bets = [0]*self.num_seats
        self.street += 1
        assert self.street <= 3
        if   self.street == 1 : self.board[:3] = cards
        elif self.street == 2 : self.board[3] = cards[0]
        else :                  self.board[4] = cards[0]


    def advanceButton( self ) :
        for pix in range( self.button+1, len(self.players) ) + \
                   range( self.button ) : 
            if not self.player[pix] == NA :
                self.button = pix

def main() :
    t = Table( num_seats=8 )
    p1 = Player("shake")
    p2 = Player("frylock")
    t.addPlayer(p1, 1)
    t.addPlayer(p2, 2)
    t.fold(1)

if __name__ == '__main__' :
    main()
