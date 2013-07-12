LOG_YEAR = 2011
LOG_DIRECTORY = "histories/acpc/%d/logs/2p_nolimit" % LOG_YEAR
TRAIN_FILENAME = "nodes/4-round_perm1_train.csv"
TEST_FILENAME = "nodes/show_4-round-perm1_test.csv"

#old
#BET_RATIOS = [0,.2,.3,.4,.5,.75,1,3]

#PAST_BET_RATIOS = [0,.2,.33,.45,.5,.6,.75,.9] #[0,.33,.5,.8]

#individual bet ratios
BET_RATIOS = ['r.44','r.5','r.75','r.81','r1','r1.33','r1.7','r4'] #[.5,1,1.6,4]
DUMMY_ACTION = 'd'

def closestRatio( ratio ) :
    return min( BET_RATIOS, key = lambda bet : abs(ratio-float(bet[1:])) )

#BUCKET_PERCENTILES = {'flop' : [.4,.1,.1] + [.05]*4 + [.02]*10, \
                      #'turn' : [.4,.1,.1] + [.05]*4 + [.02]*10, \
                      #'river': [.45,.15,.14,.05,.05,.05,.05,.02,.02,.02] }

BUCKET_PERCENTILES_SMALL = {'flop' : [.4,.2,.15,.10,.08,.07], \
                            'turn' : [.4,.3,.2,.1], \
                            'river' : [.5,.5] }

def streetname2Int( name ) :
    if name == 'preflop' : return 0
    elif name == 'flop' : return 1
    elif name == 'turn' : return 2
    elif name == 'river' : return 3
    else : assert False

def int2streetname( i ) :
    if i == 0 : return 'preflop'
    elif i == 1 : return 'flop'
    elif i == 2 : return 'turn'
    elif i == 3 : return 'river'
    else : assert False

#see exponential.py
BUCKET_PERCENTILES_EXPO = {'preflop' : [0.40003900044927887, 0.24004940056908658, 0.14407297417398401, 0.08651600755861058, 0.05202997629219996, 0.03141860537037599, 0.019185529213985624, 0.012068594181324752, 0.008169950930350486, 0.006449961260803015], \
                           'flop' : [0.25000586640034034, 0.18750635526703532, 0.1406323737393166, 0.10547775668987426, 0.07911295269792144, 0.059340894764128745, 0.04451391139401344, 0.033396420640065934, 0.025061964939457244, 0.01881600631713666, 0.01413804822124413, 0.010638260810455278, 0.008024995133871034, 0.0060804790517760415, 0.004642669557329053, 0.003591749192659485, 0.0028401412607115414, 0.0023252117671562263, 0.0020040499208639297, 0.0018498922346436276], \

                           'turn' : [0.3000164218894933, 0.21001853327528525, 0.14702302751075672, 0.10293048242618265, 0.07207185651068919, 0.05047961214657008, 0.035377603629867124, 0.02482414415128994, 0.017462360349307173, 0.012345737163663904, 0.00881642304192028, 0.006420649025566406, 0.004850387026785357, 0.003903746217162425, 0.0034590156354603763], 
                           'river' : [0.3501610588099545, 0.22769141220106134, 0.14813283943006045, 0.09649160947472483, 0.0630353366896258, 0.041458800434494715, 0.027695653492018392, 0.019152072015345536, 0.014217919495410875, 0.011963297957303649] }


BUCKET_TABLE_PREFIX = "BUCKET_EXPO_"
BUCKET_PERCENTILES = BUCKET_PERCENTILES_EXPO
NBUCKETS = [len(BUCKET_PERCENTILES['preflop']),len(BUCKET_PERCENTILES['flop']),len(BUCKET_PERCENTILES['turn']),len(BUCKET_PERCENTILES['river'])]

#consequtive, CD[0] is dist between 0,1, CD[1] between 1,2, etc
CENTROID_DISTANCES = {}
for street in BUCKET_PERCENTILES :
    percentiles = BUCKET_PERCENTILES[street]
    distances = []
    last_midpoint = 0
    for ix in range(len(percentiles)-1) :
        hp1 = percentiles[ix] / 2
        hp2 = percentiles[ix+1] / 2
        distances.append( hp1+hp2 )
    CENTROID_DISTANCES[street] = distances

#print CENTROID_DISTANCES["river"]
def bucketCentroidDistance(street,a,b) :
    if type(street) == int :
        street = int2streetname(street)
    distances = CENTROID_DISTANCES[street]
    if a == b :
        dst = 0
    elif b > a :
        dst = sum(distances[a:b])
    else :
        dst = sum(distances[b:a])

    return float(dst) #float(1) 

#def mysum(l) :
    #s = 0
    #for t in l :
        #s += t
        #print s
    #print "yes?",s
    #return s


EVALUATOR = "pokereval"
GAME = 'holdem'
NA = 'xx'
if GAME == 'holdem' or GAME == 'omaha' :
    #STREET_NAMES = ["undealt","preflop","flop","turn","river","over"]
    STREET_NAMES = [-1,0,1,2,3,4]

if GAME == 'holdem' :
    POCKET_SIZE = 2

if EVALUATOR == 'pokereval' :
    #numerical rep of a folded card
    FOLDED = 254

    #numerical rep of an unknown
    WILDCARD = 255

    #Computed EV can range from from 0-1000
    EV_RANGE = 1000


def veryClose( a,b,p=.00001 ) :
    return abs(a-b) < p
