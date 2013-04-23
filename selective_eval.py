#data file
train_filename = "nodes/training_4-rounds_showdown.csv"
test_filename = "nodes/test_4-rounds_showdown.csv"
#dist file
dist_filename = "nodes/node_10_distribution.csv"
#label file
label_filename = "nodes/node_10_labels.csv"
node_is_belief = True

#fin = open("noshow_4-round.csv")

#examine some particular subset of nodes, and return a dictionary of:
#values_nodes_take_on : frequency in file
def computeTypeFrequencies( focus_cols, given_cols, given_conditions ) :
    fin_test = open(train_filename)
    value_counts = {}
    n_not_excluded = 0
    for line_num,line in enumerate(fin_test.readlines()) :
        splt = line.strip().split(",")
        given_values = ','.join( [splt[i] for i in given_cols] )
        if not given_values in given_conditions :
            continue

        n_not_excluded += 1
        try :
            value = ','.join( [splt[i] for i in focus_cols] )

            if value in value_counts :
                value_counts[value] += 1
            else :
                value_counts[value] = 1
        except Exception as e:
            print str(e)
            print line
            print line_num,splt

    for value in value_counts :
        value_counts[value] = value_counts[value] / float(n_not_excluded)

    print 'n_not_excluded', n_not_excluded
    return value_counts


def returnMasker( focus_nodes, ignore_set ) :
    def inner( line_splt ) :
        value = ','.join( [line_splt[i] for i in focus_nodes] )
        return value in ignore_set
    return inner

    
if __name__ == '__main__' :
    given_cols = []#[11,12,13,14]
    given_conditions = ['']#['1,6,5,3']
    type_freqs =  computeTypeFrequencies( [15], given_cols, given_conditions )
    
    #find the scaling factor, such that the new example file is about the
    #same size as before
    amts = type_freqs.keys()
    percs = type_freqs.values()

    for i in range(2,5) :
        scaled_amts = [float(amt)/i for amt in amts]
        print i
        scaled_percs = [float(percs[j]) * scaled_amts[j] for j in range(len(percs))]
        print "i:",i, sum(scaled_percs)
    
    #svalues = sorted( type_freqs.keys(), key=lambda k : type_freqs[k] )
    #for v in svalues :
        #print v, "\t" , type_freqs[v]
