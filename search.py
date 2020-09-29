import re
import sys

# query = 'i:maria d:comput b:access'
query = sys.argv[2]
arr = [ i.start() for i in re.finditer(':', query)]
if len(arr)==0:
    #simple query
    words = query.split(' ')
    for word in words:
        index_ptr = open(sys.argv[1]+'/index_file','r')
        for line in index_ptr.readlines():
            line = line.strip().split(' ', 1)
            if word == line[0]:
                postings = line[1].split('|')
                for posting in postings:
                    print(posting[posting.index('d')+1:])

else:
    querymap = {}
    for i in range(len(arr)):
        if i == len(arr)-1:
            end = len(query)
        else:
            end = arr[i+1]-2
        querymap[query[arr[i]-1]] = query[arr[i]+1 : end].strip()

    print(querymap)

    for item in querymap.items():
        # index_ptr = open('/Users/mudit/Wiki/2019201063/inverted_index/index_file','r')
        index_ptr = open(sys.argv[1]+'/index_file','r')
        for line in index_ptr.readlines():
            line = line.strip().split(' ', 1)
            if item[1] == line[0]:
                postings = line[1].split('|')
                for posting in postings:
                    if item[0] in posting:
                        print(posting[posting.index('d')+1:])
