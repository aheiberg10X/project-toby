from random import sample, choice

class Player() :
    def __init__(self,name) :
        self.name = name

    def getAction( self, state ) :
        #print "player getAction"
        oblig = state.table.getObligation(state.table.action_to)
        in_final_round = state.inFinalRound()
        if oblig == 0 :
            if in_final_round :
                possible = ['k']
            else :
                possible = ['k'] + \
                           state.table.possibleRaises( \
                                         state.table.action_to, \
                                         state.raises )
        else :
            if in_final_round :
                possible = ['f','c']
            else :
                possible = ['f','c'] + \
                           state.table.possibleRaises( \
                                         state.table.action_to, \
                                         state.raises )

        #print "possible:", possible
        
        return choice(possible)

