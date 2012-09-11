from random import choice

#state is a board and a player to move (-1 or 1), and captured pieces
#board is a NxN multidim array (-1,0,1)
#maintain set of open positions coords (to sample randomly from)

class State :
    def __init__(self,dim) :
        self.dim = dim
        self.board = [0]*(dim*dim)
        self.open_spots = set(range(dim*dim))
        self.capture_counts = [0,0]
        self.player = -1

    def copy(self) : 
        ns = State(self.dim)
        ns.board = self.board
        ns.open_spots = self.open_spots
        ns.capture_counts = self.capture_counts
        ns.player = self.player
        return ns

    def getNorth(self, ix) :
        if ix < self.dim :
            return -1
        else :
            return ix - self.dim
    def getSouth(self, ix) :
        if ix >= self.dim*self.dim - self.dim :
            return -1
        else :
            return ix + self.dim
    def getEast(self, ix) :
        if ix % self.dim == self.dim - 1 :
            return -1
        else :
            return ix+1
    def getWest(self, ix) :
        if ix % self.dim == 0 :
            return -1
        else :
            return ix-1

    def action2ix( self, action ) :
        color = self.action2color(action)
        return action*color - 1

    def action2color( self, action ) :
        if action > 0 : return 1
        else          : return -1

    def ix2action( self, ix, color ) :
        return (ix+1)*color

    def setBoard( self, ixs, color ) :
        if type(ixs) == int :
            ixs = [ixs]
        for ix in ixs :
            if color != 0 :
                assert self.board[ix] == 0
            self.board[ix] = color

    def getNeighbors( self, ix ) :
        return [self.getNorth(ix), \
                self.getSouth(ix), \
                self.getEast(ix), \
                self.getWest(ix)]

    def matching( self, ixs, colors=[-1,0,1] ) :
        return [ix for ix in ixs if ix >= 0 and self.board[ix] in colors]

    def __str__(self) :
        print "Player:", self.player
        print "Captured (-1,1): ", self.capture_counts
        rows = []
        for i in range(self.dim) :
            l = []
            for j in range(self.dim) :
                p = self.board[i*self.dim+j]
                if p == -1:
                    l.append( "o"  )
                elif p == 1 :
                    l.append( "x" )
                else :
                    l.append( "-" )
            rows.append( " ".join(l) )

        return "\n".join(rows)
    
    #action ints are 1-81
    #def action2Int( self, row, col, player ) :
        ##+1 at the end to avoid 0
        #return player * ((row-1)*self.dim + (col-1) + 1)
#
    #def int2Action( self, i ) :
        #i = abs(i) - 1
        #col = i % self.dim + 1
        #row = i / self.dim + 1
        #return (row,col)

class MCTS_Go :
    def __init__(self,dim) :
        self.states = [-1,-1,State(dim)]
        self.dim = dim
        self.root_state = State(dim)

    def copyState( self, state ) :
        if type(state) == int :
            return state
        return state.copy()

    ####################################################
    ####Public Interface
    ####################################################
    def getAllowableActions( self, state ) :
        return state.open_positions

    def applyAction( self, state, action ) :
        newstates = []
        for i in range( 1, len(self.states) ) :
            newstates.append( self.copyState( self.states[i] ) )

        ix = state.action2ix(action)
        color = state.action2color(action)
        state.setBoard( ix, color )
        #TODO: resolve captures
        neighbs = state.getNeighbors( ix )
        opp_color = -color
        q = state.matching( neighbs, [opp_color] )
        marked = {}
        while len(q) > 0 :
            print "q:", q
            ix = q.pop()
            print "ix:", ix
            marked[ix] = True
            print "marked:", marked
            neighbs = state.getNeighbors( ix )
            hasEmptyNeighbs = len( state.matching( neighbs, [0] ) ) > 0
            if hasEmptyNeighbs :
                print "had empty neighbs"
                marked = {}
                break
            else :
                for n in state.matching( neighbs, [opp_color] ) :
                    if n not in marked or not marked[n] :
                        q.append(n)

        state.setBoard( [ix for ix in marked], 0 )

        #TODO: see if legal

        newstates.append( self.copyState( state ) )
        print newstates
        self.states = newstates
        #Update .states

    def getRewards( self, state ) :
        pass

    def chooseAction( self, state ) :
        return choice( self.getAllowableActions( state ) )

    def isTerminal( self, state ) :
       return len(state) >= 4

def main() :
    dim = 4
    s = State(dim)
    s.setBoard( [1,2,4,9,10], 1 )
    s.setBoard( [5,6], -1 )
    print s

    g = MCTS_Go(dim)
    g.applyAction( s, 8 )
    print s



if __name__ == '__main__' :
    main()
