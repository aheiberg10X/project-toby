#data file
test_filename = "nodes/show_test_small.csv"
#dist file
dist_filename = "nodes/node_10_distribution.csv"
#label file
label_filename = "nodes/node_10_labels.csv"
node_is_belief = True

#fin = open("noshow_4-round.csv")

#examine some particular subset of nodes, and return a dictionary of:
#values_nodes_take_on : frequency in file
def computeTypeFrequencies( focus_cols, given_cols, given_conditions ) :
    fin_test = open(test_filename)
    value_counts = {}
    n_not_excluded = 0
    for line_num,line in enumerate(fin_test.readlines()) :
        splt = line.strip().split(",")
        given_values = ','.join( [splt[i] for i in given_cols] )
        if not given_values in given_conditions :
            continue

        n_not_excluded += 1
        print splt
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
    given_cols = [9]
    given_conditions = ['9']
    type_freqs =  computeTypeFrequencies( [11], given_cols, given_conditions )
    svalues = sorted( type_freqs.keys(), key=lambda k : type_freqs[k] )
    for v in svalues :
        print v, "\t" , type_freqs[v]
    #for tipe in type_freqs :
        #print tipe, type_freqs[tipe]
