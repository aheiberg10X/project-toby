from random import choice
from deck import Deck
from table import Table
from player import Player

class State :
    def __init__(self, \
                 table, \
                 deck = Deck(), \
                 max_raise_rounds=2) :

        self.max_raise_rounds = max_raise_rounds
 
        #bet seems superfluous, it is just the first raise
        #the numbers are for raises, pot multipliers
        self.actions = ['f','k','c','r']
        self.raises = [.5,1,1.5,2,6]
        self.final_actions = ['f','k','c']

        self.table = table
        self.num_players = self.table.num_players
    
        #virtual_player % num_players represents the player in some round
        #there are only max rounds where players are free to act 
        #(i.e keep raising)
        #+1 for the final round, players must only choose from final_actions 
        self.num_virtual = (self.num_players) * (max_raise_rounds+1)

        self.deck = deck

    def inFinalRound( self ) :
        #fogetting about button offset
        #return len(self.history) >= self.num_virtual - self.num_players
        pass

    def isChanceAction( self ) :
        has_acted = self.table.acted[self.table.action_to]
        oblig_is_zero = self.table.getObligation() == 0
        return has_acted and oblig_is_zero
        #return self.table.action_to % (self.num_players+1) \
                #== self.num_players

    def copy( self ) :
        snew = State( self.stacks, \
                      self.button, \
                      self.max_raise_rounds )
        snew.history = list(self.history)
        snew.pot = self.pot
        snew.stacks = self.stacks



class MCTS_Poker :
    def __init__(self, state ) :
        self.state = state
        #self.root_state = State()
        
    def copyState(self,state) :
        return state.copy()

    def isChanceAction( self, state ) :
        return state.isChanceAction()

    def getAllowableActions( self, state ) :
        if state.isChanceAction() :
            return 'd'
        else :
            oblig = state.table.getObligation()
            in_final_round = state.inFinalRound()
            if oblig == 0 :
                if in_final_round :
                    return ['k'] + state.raises
                else :
                    return ['k']
            else :
                if in_final_round :
                    return ['f','c']
                else :
                    return ['f','c'] + state.raises

    def applyAction( self, state, action ) :
        if action == 'd' :
            state.table.advanceStreet( state.deck )

        pass

    def getRewards( self, state ) :
        pass

    def randomAction( self, state ) :
        pass

    #TODO
    #This is where we implement the naive player
    #The million dollar question
    def opponentAction(self, opp_ix, state ) :
        pass

    def isTerminal( self, state ) :
        pass

def main() :
    p1 = Player("toby")
    d = Deck()
    pockets = d.draw(2)
    p2 = Player("frylock")
    players = [p1,p2]
    t = Table(players, 0, pockets )
    s = State( t, d ) 

    mcts = MCTS_Poker( s )

    print mcts.state.table
    mcts.state.table.registerAction( 'k' )
    mcts.state.table.registerAction( 'k' )

    print mcts.state.table
    print mcts.state.isChanceAction()

if __name__ == '__main__' :
    main()
