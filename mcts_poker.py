from random import choice
from deck import Deck

class State :
    def __init__(self, stacks, button, max_raise_rounds=2) :
        self.num_players = len(stacks)
        assert num_players > 0

        self.history = []
        self.max_raise_rounds = max_raise_rounds
        self.num_players = num_players
 
        #bet seems superfluous, it is just the first raise
        #the numbers are for raises, pot multipliers
        self.actions = ['f','k','c','r']
        self.raises = [.5,1,1.5,2,6]
        self.final_actions = ['f','k','c']
    
        #virtual_player % num_players represents the player in some round
        #there are only max rounds where players are free to act 
        #(i.e keep raising)
        #+1 for the chance players, dealer of cards
        #+1 for the final round, players must only choose from final_actions 
        self.num_virtual = (self.num_players+1) * (max_raise_rounds+1)

        self.button = button
        pot = 0
        self.stacks = stacks 

        self.action_on = 0
        self.obligations = [0]*self.num_players

        self.deck = Deck()
        self.street

    def inFinalRound( self ) :
        return len(self.history) >= self.num_virtual - self.num_players

    def isChanceAction( self ) :
        return state.action_on % (state.num_players+1) == state.num_players

    def copy( self ) :
        snew = State( self.stacks, \
                      self.button, \
                      self.max_raise_rounds )
        snew.history = list(self.history)
        snew.pot = self.pot
        snew.stacks = self.stacks



class MCTS_Poker :
    def __init__(self) :
        self.root_state = State()
        
    def copyState(self,state) :
        return state.copy()

    def isChanceAction( self, state ) :
        return state.isChanceAction()

    def getAllowableActions( self, state ) :
        if state.isChanceAction() :
            #deal
            pass
        else :
            oblig = state.obligations[ state.action_on ]
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
    pass

if __name__ == '__main__' :
    main()
