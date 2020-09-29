'''
The way I am performing indexing is:
firstly , temp files are created, each sorted in itself.
Now the indexes need to be merged, so we use k-way merge.
One thing to keep in mind is searching.
Assuming index is over 10gb and sorted, we can't really use binary search as that would require
a lot of memory to be loaded in MM in run time.
So we create an additional index of offsets where with each word in inverted index, its offset (in index_file)
will be stored. This brings down the load to certain extent. But its still too big. (in orders of 2 gb)
So we need another level of indexing. For every 100000 words in offset_file, we make a new file with the same
name as the first word. Now to look for the offset we just need to find the correct file. we now can easily
apply binary search and do so.
For ranking, we consider different weights for different anchors eg title has max weight.
'''
import os
import re
from nltk.corpus import stopwords
#from nltk.stem import PorterStemmer
from Stemmer import Stemmer
import time
import sys
import math
import operator
import linecache
import numpy as np
stop_words = set(stopwords.words('english'))

stemmer = Stemmer('english')

def ranker(data,number_document,k):
    values = {}
    tag_weight = {
        't':10,
        'c':8,
        'i':5,
        'b':2,
        'l':1,
        'r':1
    }
    for word in data:
        for tag in data[word]:
            if len(data[word][tag]) == 0:
                continue
            idf = math.log(number_document/len(data[word][tag]))
            for tf in data[word][tag]:
                if tf[0] not in values:
                    values[tf[0]] = 0.0
                values[tf[0]] += idf * (math.log(tf[1]+1)+1) * tag_weight[tag]

    result = sorted(values.items(), key= operator.itemgetter(1), reverse=True)
    return result[:k]


def binary_search(list_of_files,target):
    '''
    Get the file with our offset
    '''
    l,r = 0, len(list_of_files) - 1
    while l <= r:
        mid = int(l + (r - l) / 2)
        if list_of_files[mid] < target:
            l = mid + 1
        else:
            r = mid - 1
    return list_of_files[l-1]


def getOffset(word,file_name):
    lines = np.loadtxt(file_name,dtype= str ,delimiter="\n", unpack=False)
    high = len(lines)
    low = 0
    while low <= high:
        mid = (high + low)//2
        line1 = lines[mid]
        val,offset = line1.strip().split(' ')
        line2 = lines[mid+1]
        nex_val,nex_offset = line2.strip().split(' ')
        if val == word:
            return int(offset)
        if nex_val == word:
            return int(nex_offset)
        if val < word:
            low = mid + 1
        else:
            high = mid - 1
    return -1

def get_posting_list(index_file,offset_value,key):
    '''
    since offset is ready, we go and get the word's posting list
    '''
    index_file.seek(offset_value)
    line = index_file.readline().strip().split(' ')[1].split('|')
    if key == 'all':
        return line
    value = list(v for v in line if key in v)
    return value

def searching(query,index_path,number_document,k):
    index_path = os.path.join(index_path, 'index_file.txt')
    index_file_ptr = open(index_path,'r')
    result = dict()
    list_of_files = []
    for file in os.listdir("secIndexFiles"):
        list_of_files.append(file)

    list_of_files.sort()
    for key in query:
        if key == 'all':
            for word in query['all']:
                file_name = binary_search(list_of_files,word)
                filepath = os.path.join('secIndexFiles',file_name)
                offset = getOffset(word,filepath)
                if offset == -1:
                    continue
                posting_list = get_posting_list(index_file_ptr,offset,'all')
                # print('listtt',posting_list)
                result[word] = {'t': list(), 'b': list(), 'i': list(), 'c': list(), 'l': list(), 'r': list()}
                for posting in posting_list:
                    document_id = int(re.findall('d[0-9]+',posting)[0][1:])
                    for tag in result[word].keys():
                        if tag in posting:
                            val = int(re.findall(tag+'[0-9]+', posting)[0][1:])
                            result[word][tag].append([document_id,val])
        else:
            for word in query[key]:
                file_name = binary_search(list_of_files,word)
                filepath = os.path.join('secIndexFiles',file_name)
                offset = getOffset(word,filepath)
                if offset == -1:
                    continue
                # mapping = {'title' : 't', 'body' : 'b', 'infobox': 'i', 'category': 'c', 'links':'l', 'ref' : 'r'}
                # tag = mapping[key]
                posting_list = get_posting_list(index_file_ptr, offset, key)
                if word not in result:
                    result[word] = dict()
                result[word][key] = list()
                for posting in posting_list:
                    document_id = int(re.findall('d[0-9]+',posting)[0][1:])
                    val = int(re.findall(key+'[0-9]+', posting)[0][1:])
                    result[word][key].append([document_id,val])

    ranked_result = ranker(result,number_document,k)
    return ranked_result



def get_titles():
    titles = dict()
    with open('DocId_Title_Map.txt', 'r') as file_ptr:
        for line in file_ptr.readlines():
            line = line.strip().split(' ', 1)
            if len(line) == 1:
                pass
            else:
                titles[int(line[0])] = line[1]

    return titles


def read_query_file(query_file):
    queries = list()
    with open(query_file, 'r') as file_ptr:
        for line in file_ptr.readlines():
            line = line.strip()
            queries.append(line)

    return queries

def query_processing(query):
    global stop_words
    global stemmer
    queries = dict()
    # field_reg = re.compile(r'[a-z]+:[A-Za-z0-9]+[ ]?')
    field_list = ['t:', 'b:','c:','i:','r:']
    query = query.lower()
    field_reg = re.finditer('(t:|i:|b:|c:|r:)([\w+\s+]+)(?=(t:|i:|b:|c:|r:|$))',query)
    if any(1 for field in field_list if field in query):
        #query_regex = field_reg.findall(query)
        # print("query_regex :", query_regex)
        for elem in field_reg:
            term = elem.group(0).split(":")
            #print(term)
            try:
                term_list = list(stemmer.stemWord(word.lower()) for word in term[1].split() if word not in stop_words)
                for t in term_list:
                    queries[term[0]].append(t)
            except KeyError:
                queries[term[0]] = list(stemmer.stemWord(word.lower()) for word in term[1].split() if word not in stop_words)
    else:
        words = query.strip().split(' ')
        try:
            term_list = list(stemmer.stemWord(word.lower()) for word in words if word not in stop_words)
            for t in term_list:
                queries['all'].append(t)
        except KeyError:
            queries['all'] = list(stemmer.stemWord(word.lower()) for word in words if word not in stop_words)

    return queries


if __name__ == "__main__":
#     query_list = read_query_file(sys.argv[2])
#     print("Loading Mappings...")
    titles = get_titles()
    number_document = len(titles)
    print("Loaded...")
    index_path = 'inverted_index'
    query_file = '2019201063_queries1.txt'
    output_path = 'queries_op.txt'
    query_ptr = open(query_file, 'r')
    output_ptr = open(output_path, 'w+')
    for query in query_ptr.readlines():
        start = time.time()
        k = int(query.split(',')[0])
        processed_queries = query_processing(query.split(',')[1])
        # print('query is:',processed_queries,k,query.split(',')[1])
        result = searching(processed_queries,index_path,number_document,k)
        # print("Result : ",result)
        for r in result:
            output_ptr.write(' , '.join([str(r[0]), titles[r[0]]]))
            output_ptr.write('\n')
        end = time.time()
        length = len(result)
        if length == 0:
            avg_time = '0'
            total_time = '0'
        else:
            avg_time = str((end-start)/len(result))
            total_time = str(end-start)
        output_ptr.write(total_time)
        print('time: ',total_time)
        output_ptr.write('\n\n')
