from random import choice

class MCTS_Test :
    def __init__(self) :
        self.actions = ['a','b','c']

    def getRootState(self) :
        return []

    def copyState(self,state) :
        return list(state)

    def getAllowableActions( self, state ) :
        if len(state) == 0 :
            return self.actions
        else :
            if state[-1] == 'a' :
                return ['b','c']
            elif state[-1] == 'b' :
                return ['a','c']
            elif state[-1] == 'c' :
                return ['a','b']
            else : assert False

    def applyAction( self, state, action ) :
        state.append(action)
        #return state + [action]

    def getRewards( self, state ) :
        return [ sum([elem == 'b' for elem in state]) ]

    def returnAction( self, state ) :
        return choice( self.getAllowableActions( state ) )

    def isTerminal( self, state ) :
       return len(state) >= 4

def main() :
    o = MCTS_Test()
    for i in range(10) :
        print o.chooseAction( 'abc' )


if __name__ == '__main__' :
    main()
