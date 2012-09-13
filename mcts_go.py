from random import choice

#state is a board and a player to move (-1 or 1), and captured pieces
#board is a NxN multidim array (-1,0,1)
#maintain set of open positions coords (to sample randomly from)

class State :
    def __init__(self,dim) :
        self.dim = dim
        self.board = [0]*(dim*dim)
        self.open_positions = set(range(dim*dim))
        self.capture_counts = [0,0]
        self.player = -1
        self.action = 0

    def togglePlayer(self) :
        self.player = -self.player

    def copy(self) : 
        ns = State(self.dim)
        ns.board = self.board
        ns.open_positions = self.open_positions
        ns.capture_counts = self.capture_counts
        ns.player = self.player
        return ns

    def getNorth(self, ix) :
        if ix < self.dim or ix < 0 :
            return -1
        else :
            return ix - self.dim
    def getSouth(self, ix) :
        if ix >= self.dim*self.dim - self.dim or ix < 0 :
            return -1
        else :
            return ix + self.dim
    def getEast(self, ix) :
        if ix % self.dim == self.dim - 1 or ix < 0 :
            return -1
        else :
            return ix+1
    def getWest(self, ix) :
        if ix % self.dim == 0 or ix < 0 :
            return -1
        else :
            return ix-1

    def getNorthWest(self, ix) :
        return self.getNorth( self.getWest(ix) )

    def getNorthEast(self, ix) :
        return self.getNorth( self.getEast(ix) )

    def getSouthEast(self, ix) :
        return self.getSouth( self.getEast(ix) )

    def getSouthWest(self, ix) :
        return self.getSouth( self.getWest(ix) )

    def action2ix( self, action ) :
        color = self.action2color(action)
        return action*color - 1

    def action2color( self, action ) :
        if action > 0 : return 1
        else          : return -1

    def ix2action( self, ix, color=False ) :
        if not color :
            return (ix+1)*self.ix2color(ix)
        else :
            return (ix+1)*color

    def ix2color( self, ix ) :
        return self.board[ix]

    def setBoard( self, ixs, color ) :
        if type(ixs) == int :
            ixs = [ixs]
        for ix in ixs :
            if color != 0 :
                assert self.board[ix] == 0
                self.open_positions.remove(ix)
            else :
                self.open_positions.add(ix)
            self.board[ix] = color

    def getNeighbors( self, ix, adjacency=4 ) :
        if adjacency == 4 :
            return [self.getNorth(ix), \
                    self.getSouth(ix), \
                    self.getEast(ix), \
                    self.getWest(ix)]
        elif adjacency == 8 :
            return [self.getNorth(ix), \
                    self.getSouth(ix), \
                    self.getEast(ix), \
                    self.getWest(ix), \
                    self.getNorthWest(ix), \
                    self.getNorthEast(ix), \
                    self.getSouthWest(ix), \
                    self.getSouthEast(ix) ]
        else : assert False

    def matching( self, ixs, colors=[-1,0,1] ) :
        return [ix for ix in ixs if ix >= 0 and self.board[ix] in colors]
   
    #returns a function that returns True if one ix in the neighbs list
    #matches one of the colors specified
    def hasNeighbsClosure( self, colors ) :
        def inner( neighbs ) :
            return len( self.matching( neighbs, colors ) ) > 0
        return inner

    def floodFill( self, q, colors, stopper, adjacency=4 ) :
        marked = {}
        while len(q) > 0 :
            #print "q:", q
            ix = q.pop()
            #print "ix:", ix
            marked[ix] = True
            #print "marked:", marked
            neighbs = self.getNeighbors( ix, adjacency=adjacency )
            if stopper(neighbs) :
                #print "had empty neighbs"
                marked = {}
                break
            else :
                for n in self.matching( neighbs, colors ) :
                    if n not in marked or not marked[n] :
                        q.append(n)

        return marked.keys()

    def neighboredByOneColor( self, ix, adjacency=4 ) :
        neighbs = self.getNeighbors( ix, adjacency=4 )
        has_white = len( self.matching( neighbs, [1] ) ) > 0
        has_black = len( self.matching( neighbs, [-1] ) ) > 0
        if has_white and not has_black :
            return (True,1)
        elif has_black and not has_white :
            return (True, -1)
        else :
            return (False,42)

    def __str__(self) :
        print "Player:", self.player
        print "Captured (-1,1): ", self.capture_counts
        print "Open: ", self.open_positions
        rows = []
        for i in range(self.dim) :
            l = []
            for j in range(self.dim) :
                p = self.board[i*self.dim+j]
                if   p == -1 : l.append( "o" )
                elif p == 1  : l.append( "x" )
                elif p == 0  : l.append( "-" )
                else : assert False
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

class String :
    def __init__(self,string_id,members,color) :
        self.string_id = string_id
        self.members = members
        self.color = color
        self.territories = []

    def __str__(self) :
        return "\nid: " + str(self.string_id) + \
                "\nmembers: " + str(self.members) + \
                "\ncolor: " + str(self.color) + \
                "\nterritories: " + str(self.territories)

class MCTS_Go :
    def __init__(self,dim) :
        self.states = [-1,State(dim)]
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
        #0 is pass
        return [state.ix2action(op, state.player) 
                for op 
                in state.open_positions] + [0]

    def applyAction( self, state, action ) :
        newstates = []
        for i in range( 1, len(self.states) ) :
            newstates.append( self.copyState( self.states[i] ) )

        if action != 0 :
            ix = state.action2ix(action)
            color = state.action2color(action)
            state.setBoard( ix, color )
            
            #TODO: resolve captures
            neighbs = state.getNeighbors( ix )
            opp_color = -color
            q = state.matching( neighbs, [opp_color] )

            marked = state.floodFill( q, \
                                     colors = [opp_color], \
                                     stopper = state.hasNeighbsClosure([0]) )
            state.setBoard( [ix for ix in marked], 0 )
            if color == -1 : color = 0
            state.capture_counts[color] += len(marked)

        #TODO: see if legal
        #see if the action taken will get auto-killed ... how
        #    init the queue q above to have this ix
        #    #TODO generalize this code to use it for scoring as well
        #see if the action taken makes the game the same as it was two states
        #ago
        legal = True
        if legal :
            state.togglePlayer()
            newstates.append( self.copyState( state ) )
            print newstates
            self.states = newstates
        else :
            pass
        #Update .states

    def getRewards( self, state ) :
        #find dead strings (by virtue of the 2 eye rule)
        #mark the eye-points
        #mark the dames
        #marks regions
        #mark territories
        #mark the regions that are in-seki

        #identify strings
        marked = {}
        string_id = 0
        # ix : string_id
        string_lookup = {}
        strings = {}
        for ix in range( self.dim*self.dim ) :
            if ix in state.open_positions : continue
            if ix in marked               : continue
            
            color = state.ix2color(ix)
            members = state.floodFill( [ix], \
                                      colors=[color], \
                                      stopper=lambda x:False, \
                                      adjacency=8 )

            if len(members) > 0 :
                string = String( string_id, members, color )
                for ix in members :
                    marked[ix] = True
                    string_lookup[ix] = string_id
                    strings[string_id] = string
                string_id += 1

            print "color", color, "string", string

        #TODO: loop this process
        #say we decide a string is dead, that will add some ix's to
        #open_positions and we can start again

        #for now start easy and say every string is alive
        op = list(state.open_positions)
        marked = {}
        #TODO: a territory can be bordered by more than one live string
        #how will this factor in?
        #set/list of ixs : string_id
        territories = {}
        terr_id = 0
        for ix in op :
            if ix in marked :
                continue

            color, nix = state.neighboredByOneColor( ix )
            if color :
                #TODO: flood fill returns a set or list, not a dict
                territory = state.floodFill( 
                              [ix], \
                              colors = [0], \
                              stopper = state.hasNeighbsClosure([-color]) \
                            )
                for ix in territory :
                    marked[ix] = True

                strings[string_lookup[nix]].territories.append( territory )
                territories[terr_id] = (territory, string_lookup[nix])
                terr_id += 1


                #here we know ixs in group belong to color, are territories
                
                #now need to attribute each group to different strings

            else :
                pass

        print "territories", territories
        print "strings"
        for st in strings :
            print strings[st]

    def randomAction( self, state ) :
        return choice( self.getAllowableActions( state ) )

    def isTerminal( self, state ) :
        no_legal_placement = len( self.getAllowableActions(state) ) == 1
        two_passes = self.states[-1].action == 0 and \
                     self.states[-2].action == 0
        return no_legal_placement or two_passes

def main() :
    dim = 4
    s = State(dim)
    s.setBoard( [5,6,9,10], -1 )
    s.setBoard( [1,2,4,7,8,13,14], 1 )
    print s
    g = MCTS_Go(dim)
    g.applyAction( s, 12 )
    print s
    
    s = State(dim)
    s.setBoard( [0,1,2,3,4,8,12,13,14], 1 )
    s.setBoard( [5,6,7,9,10,15], -1 )
    s.togglePlayer()
    print s
    g = MCTS_Go(dim)
    g.applyAction( s, 12 )
    print s
    print g.getAllowableActions( s )
    print g.getRewards( s )



if __name__ == '__main__' :
    main()
