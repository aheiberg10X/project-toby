from table import Table
from player import Player
from deck import Deck
from globles import NA

class Dealer() :
    def __init__(self, table) :
        self.table = table
        self.deck = Deck()

    def dealNextStreet( self ) :
        street = self.table.street
        #TODO: conceivable all remaining players count fold before next street
        #    will handle this when start on actually asking Players for actions
        players_in_hand = sum( map( lambda hc : not hc == NA, \
                                    self.table.hole_cards ) ) 
        print self.table.hole_cards
        print players_in_hand
        if players_in_hand == 1 :
            self.endHand()
            return
        elif not street == "undealt" and players_in_hand < 1 :
            assert "oh" == "noes"

        if street == "undealt" :
            cards = [self.deck.draw(2) for p in range(self.table.num_players)]
        elif street == "preflop" :
            cards = self.deck.draw(3)
        elif street == "flop" or street == "turn" :
            cards = self.deck.draw(1)
        else :
            raise Exception("Already on the river, no more streets to deal")

        self.table.advanceStreet( cards )

    def addPlayer( self, player, ix ) :
        if not self.table.street == "undealt" :
            raise Exception("Can't add a player once the game has started")
        self.table.addPlayer( player, ix )

    #TODO
    def amountIsLegal( self, amount ) :
        return True

    def check( self, player_ix ) :
        assert max(self.table.current_bets) == 0
        self.table.registerAction( player_ix, 'k' )

    def fold( self, player_ix ) :
        self.table.registerAction( player_ix, 'f' )

    def call( self, player_ix ) :
        bet_to_call = max(self.table.current_bets)
        already_bet = self.table.current_bets[player_ix]
        assert bet_to_call > already_bet
        self.table.registerAction( player_ix, 'b', bet_to_call-already_bet )

    def bet( self, player_ix, amount ) :
        assert max(self.table.current_bets) == 0
        assert self.amountIsLegal( amount )
        self.table.registerAction( player_ix, 'b', amount )

    #the amount of the raise, not including the call amount
    def raze( self, player_ix, amount ) :
        assert max(self.table.current_bets) > 0
        assert self.amountIsLegal( amount )
        self.table.registerAction( player_ix, 'r', amount )

    #end the game, figure out payouts, log the game history, reset table
    def endHand(self) :
        self.table.reset()

    def endGame(self) :
        self.table.close()


def main() :
    t = Table( num_seats=8 )
    d = Dealer( t )
    p1 = Player("shake")
    p2 = Player("frylock")
    d.addPlayer(p1, 1)
    d.addPlayer(p2, 2)
    d.dealNextStreet()
    d.check(1)
    d.check(2)
    #action
    #action
    d.dealNextStreet()
    d.bet(1,100)
    d.fold(2)
    d.dealNextStreet()
    d.dealNextStreet()
    d.endHand()

    d.endGame()


    #t.registerAction('f',1)

if __name__ == '__main__' :
    main()

