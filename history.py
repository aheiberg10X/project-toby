import datetime

class History() :
    def __init__(self) :
        self.num_actions = 0
        dt = str(datetime.datetime.now()).replace(' ','_')[:-7]
        self.log = open( "gamelogs/%s.gamelog" % dt, 'w' )

    def __del__(self) :
        self.log.close()

    def update(self, action_tuple) :
        self.log.write( "%s\n" % str(action_tuple) )
        self.num_actions += 1
