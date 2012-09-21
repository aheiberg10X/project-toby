from random import choice, sample
from deck import Deck, deCanonicalize, canonicalize, makeHuman
from table import Table
from player import Player
from pokereval import PokerEval
from globles import GAME

class State :
    def __init__(self, \
                 table, \
                 true_deck = Deck(), \
                 max_raise_rounds=2) :

        self.max_raise_rounds = max_raise_rounds
 
        #the numbers are for raises, pot multipliers
        #bet  is superfluous, it is first raise
        #call is superfluous, it is       raise with a pot fraction = 0
        self.actions = ['f','k','c','r']
        self.raises = [.33,.5,.66,.75,1.0,3.0,6.0]
        self.final_actions = ['f','k','c']

        self.table = table
        self.num_players = self.table.num_players
    
        #virtual_player % num_players represents the player in some round
        #there are only max rounds where players are free to act 
        #(i.e keep raising)
        #+1 for the final round, players must only choose from final_actions 
        self.num_virtual = (self.num_players) * (max_raise_rounds+1)

        self.true_deck = true_deck

    def inFinalRound( self ) :
        #fogetting about button offset?
        return len(self.table.history[self.table.street]) >= \
               self.num_virtual - self.num_players
        pass

#TODO all this stuff looks like it belongs in Table

    def isDealerAction( self ) :
        has_acted = self.table.acted[self.table.action_to]
        oblig_is_zero = self.table.getObligation(self.table.action_to) == 0
        return has_acted and oblig_is_zero
        #return self.table.action_to % (self.num_players+1) \
                #== self.num_players

    def isChanceAction( self ) : 
        return self.isDealerAction() or \
               not self.table.action_to == self.table.toby_ix

    def playersAlive( self ) :
        alive = []
        for i in range(self.num_players) :
            if not self.table.folded[i] :
                alive.append(i)
        return alive
    
    def copy( self ) :
        snew = State( self.stacks, \
                      self.button, \
                      self.max_raise_rounds )
        snew.history = list(self.history)
        snew.pot = self.pot
        snew.stacks = self.stacks

class MCTS_Poker :
    def __init__(self ) :
        #self.state = state
        self.pe = PokerEval()
        self.sim_deck = Deck()
        #self.root_state = State()
        
    def copyState(self,state) :
        return state.copy()

    def isChanceAction( self, state ) :
        return state.isChanceAction()

    #return False if no available action
    def randomAction( self, state, excluded=set() ) :
        #we ignore excluded for these
        if state.isChanceAction() :
            if state.isDealerAction() :
                if state.table.street == "preflop" :
                    cards = self.sim_deck.draw(3)
                elif state.table.street == "flop" or \
                     state.table.street == "turn" :
                    cards = self.sim_deck.draw(1)
                return "d%s" % canonicalize(cards)
            else :
                player = state.table.players[state.table.action_to]
                return player.getAction( state )

        else :
            assert state.table.action_to == state.table.toby_ix
            oblig = state.table.getObligation(state.table.action_to)
            in_final_round = state.inFinalRound()
            assert False
            #inFinalRounds is being all gay still
            if oblig == 0 :
                if in_final_round :
                    possible = ['k']
                else :
                    possible = ['k'] + \
                               state.table.possibleRaises( \
                                             state.table.toby_ix, \
                                             state.raises )
            else :
                if in_final_round :
                    possible = ['f','c']
                else :
                    possible = ['f','c'] + \
                               state.table.possibleRaises( \
                                             state.table.toby_ix, \
                                             state.raises )

            #TODO: does expansion really need to be random?
            #TODO: might want to collapse raises into 'r', 
            #then if 'r' is picked randomly pick an amount
            #one the other hand what is the point, UCT will be doing
            #smart selection for us
            #oh but this is used for defaultPolicy to, but nm that falls
            #under chance nodes....
            #then again not when simulating toby's decisions....
            print "possible:", possible
            for p in sample( possible, len(possible) ) :
                if p not in excluded :
                    return p

            return False

    def applyAction( self, state, action ) :
        if type(action) == str and action.startswith('d') :
            state.table.advanceStreet( deCanonicalize(action) )
        else :
            if type(action) == float :
                state.table.registerAction( 'r', action )
            else :
                state.table.registerAction( action )

    def getRewards( self, state ) :
        #need to know the pockets here, take them out of the deck
        #in general we need a 'true' deck, and a simulation deck
        assert self.isTerminal(state)
        rewards = [0]*state.num_players

        alive = state.playersAlive()
        one_alive = len(alive) == 1
        if one_alive :
            state.table.collectBets()
            winners = alive
            num_winners = 1
        else :
            #shouln't be doing this here
            assert state.table.street == "river"
            #while state.table.street != "river" :
                #cards = self.randomAction( state )
                #state.table.advanceStreet( deCanonicalize(cards) )
            
            winners = self.pe.winners( game=GAME, \
                                       pockets=state.table.pockets, \
                                       board=state.table.board )
            winners = winners['hi']
            num_winners = float(len(winners))
        
        for i in range(state.num_players) :
            if i in winners :
                rewards[i] = state.table.pot / num_winners

        return rewards

    def isTerminal( self, state ) :
        one_alive = len(state.playersAlive()) == 1

        #this isn't really terminal, dealer still needs to take actions
        #only_one_stack_left = sum([state.table.stacks[pix] > 0 \
                                   #for pix \
                                   #in range(state.table.num_players)
                                   #if not state.table.folded[pix] ]) == 1 

        showdown = state.isDealerAction() and \
                   (state.table.street == 'river' )#or \
                    #only_one_stack_left)
        print "one_alive", one_alive
        print "showdown", showdown
        return one_alive or showdown

def main() :
    if True :
        p1 = Player("toby")
        true_deck = Deck()
        toby_ix = 0
        pockets = [true_deck.draw(2), true_deck.draw(2)]
        p2 = Player("frylock")
        players = [p1,p2]
        stacks = [15,100]
        t = Table(players, stacks, toby_ix, pockets )
        t.pot = 3
        s = State( t, true_deck ) 
        mcts = MCTS_Poker()
        print s.table
       
        for i in range(20) :
            action = mcts.randomAction( s )
            print "\naction: ", action
            mcts.applyAction( s, action )
            print s.table.board
            print s.table
            if mcts.isTerminal( s ) :
                print "rewards: ", mcts.getRewards( s )
                break


    if False :
        p1 = Player("toby")
        d = Deck()
        toby_ix = 0
        pockets = [d.draw(2), d.draw(2)]
        p2 = Player("frylock")
        players = [p1,p2]
        stacks = [1.5,100]
        t = Table(players, stacks, toby_ix, pockets )
        t.pot = 3
        s = State( t, d ) 

        mcts = MCTS_Poker()

        print s.table
        s.table.registerAction( 'k' )
        s.table.registerAction( 'r', .5 )
        s.table.registerAction( 'r', .5 )
        #since toby is out of money here, frylock should auto-check
        #or rather getAllowableActions should only return k here
        
        print s.table

        #print "final round?: ",mcts.state.inFinalRound()
        #print "Allowable: ", mcts.getAllowableActions( s )
        #mcts.state.table.registerAction( 'k' )
        s.table.registerAction( 'f' )

        print "terminal?: ", mcts.isTerminal(s)
        print "rewards:", mcts.getRewards(s)
        print s.table

if __name__ == '__main__' :
    main()
