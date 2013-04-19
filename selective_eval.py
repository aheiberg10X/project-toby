fin = open("show_4-round.csv")
#fin = open("noshow_4-round.csv")
cols = [11,12,13,14]
value_counts = {}
for line_num,line in enumerate(fin.readlines()) :
    splt = line.strip().split(",")
    #print splt
    try :
        value = ','.join( [splt[i] for i in cols] )
        if value in value_counts :
            value_counts[value] += 1
        else :
            value_counts[value] = 1
    except Exception :
        print line
        print line_num,splt

svalues = sorted( value_counts.keys(), key=lambda k : value_counts[k] )
for v in svalues :
    print v, "\t" , value_counts[v]/ float(line_num)
